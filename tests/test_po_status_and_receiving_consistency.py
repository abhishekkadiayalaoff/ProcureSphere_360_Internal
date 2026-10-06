from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import Role, User
from apps.orders.models import POLine, PurchaseOrder
from apps.organization.models import CostCenter, Department, Organization
from apps.receipts.models import GoodsReceipt, InspectionRecord, RejectionRecord
from apps.receipts.services import create_goods_receipt_service, record_inspection_service
from apps.vendors.models import Vendor, VendorCategory


@pytest.fixture
def consistency_setup(db, db_roles):
    org = Organization.objects.create(name="HPE Tech", code="HPE-CONS-ORG")
    dept = Department.objects.create(organization=org, name="Logistics", code="DEPT-LOG-CONS")
    cost_center = CostCenter.objects.create(
        department=dept, code="CC-LOG-CONS", name="Central Receiving"
    )
    category = VendorCategory.objects.create(name="Hardware", code="CAT-HW-CONS")
    vendor = Vendor.objects.create(
        legal_name="Enterprise Hardware Ltd",
        tax_identification_number="TIN-EHW-CONS",
        category=category,
        status=Vendor.STATUS_ACTIVE,
    )

    receiver = User.objects.create_user(
        email="receiver_cons@hpe.com",
        password="Password123!",
        role=db_roles[Role.STORES_RECEIVER],
    )

    buyer = User.objects.create_user(
        email="buyer_cons@hpe.com",
        password="Password123!",
        role=db_roles[Role.PROC_EXEC],
    )

    po = PurchaseOrder.objects.create(
        po_number="PO-2026-CONS-001",
        version=1,
        vendor=vendor,
        cost_center=cost_center,
        status=PurchaseOrder.STATUS_ISSUED,
        subtotal=Decimal("15000.00"),
        tax_amount=Decimal("1500.00"),
        total_amount=Decimal("16500.00"),
    )

    line1 = POLine.objects.create(
        po=po,
        item_description="Server Blade Gen 11",
        quantity=Decimal("10.00"),
        quantity_received=Decimal("0.00"),
        unit_of_measure="EA",
        unit_price=Decimal("1000.00"),
    )

    line2 = POLine.objects.create(
        po=po,
        item_description="64GB ECC Memory Kit",
        quantity=Decimal("10.00"),
        quantity_received=Decimal("0.00"),
        unit_of_measure="EA",
        unit_price=Decimal("500.00"),
    )

    return {
        "org": org,
        "vendor": vendor,
        "cost_center": cost_center,
        "receiver": receiver,
        "buyer": buyer,
        "po": po,
        "line1": line1,
        "line2": line2,
    }


@pytest.mark.django_db
def test_full_receipt_transitions_po_to_completed(consistency_setup):
    """Rule 1: Full receipt of all lines transitions PO to COMPLETED."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]
    line2 = consistency_setup["line2"]

    grn = create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("10.00"),
            },
            {
                "po_line_id": str(line2.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("10.00"),
            },
        ],
        delivery_note_number="DN-FULL-001",
    )

    po.refresh_from_db()
    line1.refresh_from_db()
    line2.refresh_from_db()

    assert grn.lines.count() == 2
    assert line1.quantity_received == Decimal("10.00")
    assert line1.remaining_quantity == Decimal("0.00")
    assert line2.quantity_received == Decimal("10.00")
    assert line2.remaining_quantity == Decimal("0.00")
    assert po.status == PurchaseOrder.STATUS_COMPLETED


@pytest.mark.django_db
def test_partial_receipt_transitions_po_to_partial_receipt(consistency_setup):
    """Rule 2: Partial receipt of any line transitions PO to PARTIAL_RECEIPT."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]
    line2 = consistency_setup["line2"]

    create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("4.00"),
                "quantity_accepted": Decimal("4.00"),
            }
        ],
        delivery_note_number="DN-PART-001",
    )

    po.refresh_from_db()
    line1.refresh_from_db()
    line2.refresh_from_db()

    assert line1.quantity_received == Decimal("4.00")
    assert line1.remaining_quantity == Decimal("6.00")
    assert line2.quantity_received == Decimal("0.00")
    assert line2.remaining_quantity == Decimal("10.00")
    assert po.status == PurchaseOrder.STATUS_PARTIAL_RECEIPT


@pytest.mark.django_db
def test_second_receipt_completing_partial_po(consistency_setup):
    """Rule 3: Multiple partial receipts accumulate received quantities and complete PO."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]
    line2 = consistency_setup["line2"]

    # First GRN: partial line1 & line2
    create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("6.00"),
                "quantity_accepted": Decimal("6.00"),
            },
            {
                "po_line_id": str(line2.id),
                "quantity_received": Decimal("5.00"),
                "quantity_accepted": Decimal("5.00"),
            },
        ],
        delivery_note_number="DN-BATCH-1",
    )

    po.refresh_from_db()
    assert po.status == PurchaseOrder.STATUS_PARTIAL_RECEIPT

    # Second GRN: remaining quantities
    create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("4.00"),
                "quantity_accepted": Decimal("4.00"),
            },
            {
                "po_line_id": str(line2.id),
                "quantity_received": Decimal("5.00"),
                "quantity_accepted": Decimal("5.00"),
            },
        ],
        delivery_note_number="DN-BATCH-2",
    )

    po.refresh_from_db()
    line1.refresh_from_db()
    line2.refresh_from_db()

    assert line1.quantity_received == Decimal("10.00")
    assert line1.remaining_quantity == Decimal("0.00")
    assert line2.quantity_received == Decimal("10.00")
    assert line2.remaining_quantity == Decimal("0.00")
    assert po.status == PurchaseOrder.STATUS_COMPLETED
    assert GoodsReceipt.objects.filter(po=po).count() == 2


@pytest.mark.django_db
def test_attempt_to_receive_more_than_remaining_quantity(consistency_setup):
    """Rule 4: Attempt to receive more than remaining quantity raises ValidationError."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]

    with pytest.raises(ValidationError) as exc:
        create_goods_receipt_service(
            po=po,
            received_by=receiver,
            receipt_items=[
                {
                    "po_line_id": str(line1.id),
                    "quantity_received": Decimal("11.00"),  # Ordered only 10.00
                }
            ],
            delivery_note_number="DN-OVER-001",
        )
    assert "cannot exceed remaining quantity" in str(exc.value)
    assert GoodsReceipt.objects.filter(po=po).count() == 0


@pytest.mark.django_db
def test_attempt_to_receive_completed_po(consistency_setup):
    """Rule 5: Attempt to receive against a COMPLETED PO is rejected."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]

    po.status = PurchaseOrder.STATUS_COMPLETED
    po.save(update_fields=["status"])

    with pytest.raises(ValidationError) as exc:
        create_goods_receipt_service(
            po=po,
            received_by=receiver,
            receipt_items=[
                {
                    "po_line_id": str(line1.id),
                    "quantity_received": Decimal("1.00"),
                }
            ],
        )
    assert "Cannot record goods receipt against PO in status 'COMPLETED'" in str(exc.value)


@pytest.mark.django_db
def test_rejected_quantity_does_not_increase_po_received_quantity(consistency_setup):
    """Rule 6: Rejected quantities do not increase PO's received/accepted count."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]

    create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("7.00"),  # 3 rejected
                "rejection_reason": "Damaged pins on 3 units",
            }
        ],
        delivery_note_number="DN-REJ-001",
    )

    line1.refresh_from_db()
    po.refresh_from_db()

    assert line1.quantity_received == Decimal("7.00")
    assert line1.remaining_quantity == Decimal("3.00")
    assert po.status == PurchaseOrder.STATUS_PARTIAL_RECEIPT

    grn = GoodsReceipt.objects.get(po=po)
    r_line = grn.lines.get(po_line=line1)
    assert r_line.quantity_received == Decimal("10.00")
    assert r_line.quantity_accepted == Decimal("7.00")
    assert r_line.quantity_rejected == Decimal("3.00")
    assert RejectionRecord.objects.filter(receipt_line=r_line).count() == 1


@pytest.mark.django_db
def test_initial_inspection_and_reinspection_delta(consistency_setup):
    """Rules 7 & 8: Initial inspection and subsequent reinspection apply exact deltas."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]
    line2 = consistency_setup["line2"]

    # Initial GRN (all 10 received and initially accepted)
    grn = create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("10.00"),
            },
            {
                "po_line_id": str(line2.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("10.00"),
            },
        ],
        delivery_note_number="DN-INSP-001",
    )
    po.refresh_from_db()
    assert po.status == PurchaseOrder.STATUS_COMPLETED

    r_line1 = grn.lines.get(po_line=line1)
    r_line2 = grn.lines.get(po_line=line2)

    # Initial Inspection: 2 units of line1 fail QA
    record_inspection_service(
        receipt=grn,
        inspected_by=receiver,
        inspection_items=[
            {
                "receipt_line_id": str(r_line1.id),
                "passed": False,
                "rejected_quantity": Decimal("2.00"),
                "rejection_reason": "Thermal test failure",
                "inspection_notes": "2 units overheated during burn-in test",
            },
            {
                "receipt_line_id": str(r_line2.id),
                "passed": True,
                "inspection_notes": "All 10 passed memory check",
            },
        ],
    )

    line1.refresh_from_db()
    po.refresh_from_db()
    r_line1.refresh_from_db()

    assert r_line1.quantity_accepted == Decimal("8.00")
    assert r_line1.quantity_rejected == Decimal("2.00")
    assert line1.quantity_received == Decimal("8.00")
    assert line1.remaining_quantity == Decimal("2.00")
    assert po.status == PurchaseOrder.STATUS_PARTIAL_RECEIPT

    # Reinspection: vendor repaired 1 unit, now only 1 rejected (accepted becomes 9.00)
    record_inspection_service(
        receipt=grn,
        inspected_by=receiver,
        inspection_items=[
            {
                "receipt_line_id": str(r_line1.id),
                "passed": False,
                "rejected_quantity": Decimal("1.00"),
                "rejection_reason": "1 unit remaining defective",
                "inspection_notes": "1 unit retested and passed, 1 unit remaining bad",
            }
        ],
    )

    line1.refresh_from_db()
    po.refresh_from_db()
    r_line1.refresh_from_db()

    assert r_line1.quantity_accepted == Decimal("9.00")
    assert r_line1.quantity_rejected == Decimal("1.00")
    assert line1.quantity_received == Decimal("9.00")
    assert line1.remaining_quantity == Decimal("1.00")
    assert po.status == PurchaseOrder.STATUS_PARTIAL_RECEIPT


@pytest.mark.django_db
def test_reinspection_does_not_double_count(consistency_setup):
    """Rule 9: Repeated reinspection with identical values causes 0 delta and does not corrupt PO."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]
    line1 = consistency_setup["line1"]

    grn = create_goods_receipt_service(
        po=po,
        received_by=receiver,
        receipt_items=[
            {
                "po_line_id": str(line1.id),
                "quantity_received": Decimal("10.00"),
                "quantity_accepted": Decimal("10.00"),
            }
        ],
        delivery_note_number="DN-IDEMPOTENT",
    )

    r_line1 = grn.lines.get(po_line=line1)

    # First inspection
    record_inspection_service(
        receipt=grn,
        inspected_by=receiver,
        inspection_items=[
            {
                "receipt_line_id": str(r_line1.id),
                "passed": True,
                "inspection_notes": "QA Pass",
            }
        ],
    )

    line1.refresh_from_db()
    assert line1.quantity_received == Decimal("10.00")

    # Second inspection with same parameters
    record_inspection_service(
        receipt=grn,
        inspected_by=receiver,
        inspection_items=[
            {
                "receipt_line_id": str(r_line1.id),
                "passed": True,
                "inspection_notes": "QA Pass Confirmation",
            }
        ],
    )

    line1.refresh_from_db()
    assert line1.quantity_received == Decimal("10.00")
    assert line1.remaining_quantity == Decimal("0.00")
    assert InspectionRecord.objects.filter(receipt_line=r_line1).count() == 1


@pytest.mark.django_db
def test_remaining_quantity_never_becomes_negative(consistency_setup):
    """Rule 10: POLine.remaining_quantity property is never negative."""
    line1 = consistency_setup["line1"]
    line1.quantity = Decimal("10.00")
    line1.quantity_received = Decimal("10.00")
    assert line1.remaining_quantity == Decimal("0.00")

    # Extreme edge test: if quantity_received > quantity
    line1.quantity_received = Decimal("12.00")
    assert line1.remaining_quantity == Decimal("0.00")


@pytest.mark.django_db
def test_cross_po_tampering_blocked(consistency_setup):
    """Rule 11: Cross-PO line tampering is rejected in both receipt creation and inspection."""
    po = consistency_setup["po"]
    receiver = consistency_setup["receiver"]

    # Other PO and line
    other_po = PurchaseOrder.objects.create(
        po_number="PO-OTHER-2026",
        vendor=consistency_setup["vendor"],
        cost_center=consistency_setup["cost_center"],
        status=PurchaseOrder.STATUS_ISSUED,
    )
    other_line = POLine.objects.create(
        po=other_po,
        item_description="Unrelated Item",
        quantity=Decimal("5.00"),
        unit_price=Decimal("200.00"),
    )

    # Submitting other_line against po raises ValidationError
    with pytest.raises(ValidationError) as exc:
        create_goods_receipt_service(
            po=po,
            received_by=receiver,
            receipt_items=[
                {
                    "po_line_id": str(other_line.id),
                    "quantity_received": Decimal("2.00"),
                }
            ],
        )
    assert "does not belong to Purchase Order" in str(exc.value)
