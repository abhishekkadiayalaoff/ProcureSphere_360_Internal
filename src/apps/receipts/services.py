from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.orders.models import POLine, PurchaseOrder

from .models import GoodsReceipt, InspectionRecord, ReceiptLine, RejectionRecord


def _validate_and_create_receipt_line(
    *,
    receipt: GoodsReceipt,
    po: PurchaseOrder,
    received_by: User,
    item: dict,
) -> None:
    po_line_id = item.get("po_line_id") or (item["po_line"].id if "po_line" in item else None)
    if not po_line_id:
        raise ValidationError("Invalid receipt line: missing PO line reference.")

    po_line = POLine.objects.select_for_update().get(id=po_line_id)

    if po_line.po_id != po.id:
        raise ValidationError(
            f"PO line {po_line.id} does not belong to Purchase Order {po.po_number}."
        )

    qty_received = Decimal(str(item["quantity_received"]))
    if qty_received <= Decimal("0.00"):
        raise ValidationError(
            f"Quantity received for '{po_line.item_description}' must be greater than 0."
        )

    remaining_qty = po_line.quantity - (po_line.quantity_received or Decimal("0.00"))
    if qty_received > remaining_qty:
        raise ValidationError(
            f"Quantity received ({qty_received}) cannot exceed remaining quantity ({remaining_qty}) for '{po_line.item_description}'."
        )

    qty_accepted = Decimal(str(item.get("quantity_accepted", qty_received)))
    if qty_accepted < Decimal("0.00"):
        raise ValidationError(
            f"Quantity accepted for '{po_line.item_description}' cannot be negative."
        )
    if qty_accepted > qty_received:
        raise ValidationError(
            f"Quantity accepted ({qty_accepted}) cannot exceed quantity received ({qty_received}) for '{po_line.item_description}'."
        )

    qty_rejected = qty_received - qty_accepted

    line = ReceiptLine.objects.create(
        receipt=receipt,
        po_line=po_line,
        quantity_received=qty_received,
        quantity_accepted=qty_accepted,
        quantity_rejected=qty_rejected,
        notes=item.get("notes", ""),
    )

    if "inspection_notes" in item:
        InspectionRecord.objects.create(
            receipt_line=line,
            inspected_by=received_by,
            passed=(qty_rejected == Decimal("0.00")),
            inspection_notes=item["inspection_notes"],
        )

    if qty_rejected > Decimal("0.00"):
        RejectionRecord.objects.create(
            receipt_line=line,
            rejected_quantity=qty_rejected,
            rejection_reason=item.get("rejection_reason", "Quality non-conformance"),
        )

    po_line.quantity_received += qty_accepted
    po_line.save(update_fields=["quantity_received", "updated_at"])


def _update_po_completion_status(po: PurchaseOrder) -> None:
    all_completed = True
    for line in POLine.objects.filter(po=po):
        if line.quantity_received < line.quantity:
            all_completed = False
            break

    po.status = (
        PurchaseOrder.STATUS_COMPLETED if all_completed else PurchaseOrder.STATUS_PARTIAL_RECEIPT
    )
    po.save(update_fields=["status", "updated_at"])


@transaction.atomic
def create_goods_receipt_service(
    *,
    po: PurchaseOrder,
    received_by: User,
    receipt_items: list,
    delivery_note_number: str = "",
    remarks: str = "",
) -> GoodsReceipt:
    """
    Records a Goods Receipt Note (GRN) against a Purchase Order.
    Supports partial receipts and multiple GRNs against one PO.
    Updates POLine.quantity_received and transitions PO status (PARTIAL_RECEIPT vs COMPLETED).
    """
    if po.status not in [
        PurchaseOrder.STATUS_ISSUED,
        PurchaseOrder.STATUS_ACKNOWLEDGED,
        PurchaseOrder.STATUS_PARTIAL_RECEIPT,
    ]:
        raise ValidationError(f"Cannot record goods receipt against PO in status '{po.status}'.")

    if not receipt_items:
        raise ValidationError("Receipt must contain at least one line item.")

    grn_count = GoodsReceipt.objects.count() + 1
    grn_number = f"GRN-{timezone.now().strftime('%Y')}-{grn_count:05d}"

    receipt = GoodsReceipt.objects.create(
        grn_number=grn_number,
        po=po,
        received_by=received_by,
        received_date=timezone.now(),
        delivery_note_number=delivery_note_number,
        remarks=remarks,
    )

    for item in receipt_items:
        _validate_and_create_receipt_line(
            receipt=receipt,
            po=po,
            received_by=received_by,
            item=item,
        )

    _update_po_completion_status(po)

    AuditLog.objects.create(
        actor=received_by,
        action=AuditLog.ACTION_CREATE,
        target_model="GoodsReceipt",
        target_object_id=str(receipt.id),
        new_state={
            "grn_number": receipt.grn_number,
            "po_number": po.po_number,
            "po_status": po.status,
        },
    )

    return receipt


def _sync_rejection_record(
    receipt_line: ReceiptLine,
    qty_rejected: Decimal,
    item: dict,
    inspection_notes: str,
) -> None:
    if qty_rejected > Decimal("0.00"):
        rejection_reason = (
            item.get("rejection_reason", "").strip()
            or f"Quality rejection of {qty_rejected} units: {inspection_notes or 'Defective/Damaged'}"
        )
        returned_to_vendor = bool(item.get("returned_to_vendor", False))

        existing_rejection = RejectionRecord.objects.filter(receipt_line=receipt_line).first()
        if existing_rejection:
            existing_rejection.rejected_quantity = qty_rejected
            existing_rejection.rejection_reason = rejection_reason
            existing_rejection.returned_to_vendor = returned_to_vendor
            existing_rejection.save(
                update_fields=[
                    "rejected_quantity",
                    "rejection_reason",
                    "returned_to_vendor",
                    "updated_at",
                ]
            )
        else:
            RejectionRecord.objects.create(
                receipt_line=receipt_line,
                rejected_quantity=qty_rejected,
                rejection_reason=rejection_reason,
                returned_to_vendor=returned_to_vendor,
            )
    else:
        RejectionRecord.objects.filter(receipt_line=receipt_line).delete()


def _apply_single_line_inspection(
    *,
    receipt: GoodsReceipt,
    po: PurchaseOrder,
    inspected_by: User,
    item: dict,
) -> bool:
    receipt_line_id = item.get("receipt_line_id") or (
        item["receipt_line"].id if "receipt_line" in item else None
    )
    if not receipt_line_id:
        raise ValidationError("Invalid inspection item: missing ReceiptLine reference.")

    receipt_line = (
        ReceiptLine.objects.select_for_update().select_related("po_line").get(id=receipt_line_id)
    )

    if receipt_line.receipt_id != receipt.id or receipt_line.po_line.po_id != po.id:
        raise ValidationError(
            f"Receipt line {receipt_line.id} does not match Goods Receipt or PO reference."
        )

    passed = bool(item.get("passed", True))
    inspection_notes = str(item.get("inspection_notes", "")).strip()

    rejected_qty_raw = item.get("rejected_quantity")
    if rejected_qty_raw is not None and str(rejected_qty_raw).strip() != "":
        qty_rejected = Decimal(str(rejected_qty_raw))
    else:
        qty_rejected = Decimal("0.00") if passed else receipt_line.quantity_received

    if qty_rejected < Decimal("0.00") or qty_rejected > receipt_line.quantity_received:
        raise ValidationError("Invalid rejected quantity specified for receipt line.")

    qty_accepted = receipt_line.quantity_received - qty_rejected
    if qty_rejected > Decimal("0.00"):
        passed = False

    old_accepted = receipt_line.quantity_accepted
    delta_accepted = qty_accepted - old_accepted
    po_line_updated = False

    if delta_accepted != Decimal("0.00"):
        po_line = POLine.objects.select_for_update().get(id=receipt_line.po_line_id)
        po_line.quantity_received = max(Decimal("0.00"), po_line.quantity_received + delta_accepted)
        po_line.save(update_fields=["quantity_received", "updated_at"])
        po_line_updated = True

    receipt_line.quantity_accepted = qty_accepted
    receipt_line.quantity_rejected = qty_rejected
    receipt_line.save(update_fields=["quantity_accepted", "quantity_rejected", "updated_at"])

    InspectionRecord.objects.update_or_create(
        receipt_line=receipt_line,
        defaults={
            "inspected_by": inspected_by,
            "passed": passed,
            "inspection_notes": inspection_notes
            or f"Inspection {'PASSED' if passed else 'FAILED'}",
        },
    )

    _sync_rejection_record(receipt_line, qty_rejected, item, inspection_notes)
    return po_line_updated


@transaction.atomic
def record_inspection_service(
    *,
    receipt: GoodsReceipt,
    inspected_by: User,
    inspection_items: list,
) -> GoodsReceipt:
    """
    Records or updates quality inspection and rejection records for a Goods Receipt Note (GRN).
    Enforces server-side quantity validation, ownership verification, and updates PO line quantities.
    """
    if not inspection_items:
        raise ValidationError("Inspection must contain results for at least one line item.")

    po = receipt.po
    po_lines_updated = False

    for item in inspection_items:
        updated = _apply_single_line_inspection(
            receipt=receipt,
            po=po,
            inspected_by=inspected_by,
            item=item,
        )
        if updated:
            po_lines_updated = True

    if po_lines_updated:
        _update_po_completion_status(po)

    AuditLog.objects.create(
        actor=inspected_by,
        action=AuditLog.ACTION_UPDATE,
        target_model="GoodsReceipt",
        target_object_id=str(receipt.id),
        new_state={
            "grn_number": receipt.grn_number,
            "action": "RECORD_INSPECTION",
            "po_number": po.po_number,
            "inspected_lines_count": len(inspection_items),
        },
    )

    return receipt
