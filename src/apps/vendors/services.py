from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.audit.services import create_audit_log_service
from apps.core.validators import validate_file_upload
from apps.notifications.models import Notification
from apps.notifications.services import notify_vendor_users

from .models import Vendor, VendorCategory, VendorDocument, VendorRiskRecord


@transaction.atomic
def register_vendor_service(
    *,
    legal_name: str,
    tax_identification_number: str,
    category: VendorCategory,
    email: str,
    address: str,
    trade_name: str = "",
    registration_number: str = "",
    phone: str = "",
    bank_name: str = "",
    bank_account_number: str = "",
    bank_routing_code: str = "",
    created_by_user: User = None,
) -> Vendor:
    """
    Registers a new vendor in DRAFT status with unique vendor number.
    """
    if Vendor.objects.filter(tax_identification_number=tax_identification_number).exists():
        raise ValidationError(f"Vendor with tax ID '{tax_identification_number}' already exists.")

    vendor_count = Vendor.objects.count() + 1
    vendor_number = f"VND-{timezone.now().strftime('%Y')}-{vendor_count:05d}"

    vendor = Vendor.objects.create(
        legal_name=legal_name,
        trade_name=trade_name,
        vendor_number=vendor_number,
        tax_identification_number=tax_identification_number,
        registration_number=registration_number,
        category=category,
        email=email,
        phone=phone,
        address=address,
        bank_name=bank_name,
        bank_account_number=bank_account_number,
        bank_routing_code=bank_routing_code,
        status=Vendor.STATUS_DRAFT,
        created_by=created_by_user,
    )

    AuditLog.objects.create(
        actor=created_by_user,
        action=AuditLog.ACTION_CREATE,
        target_model="Vendor",
        target_object_id=str(vendor.id),
        new_state={
            "status": vendor.status,
            "vendor_number": vendor.vendor_number,
            "legal_name": vendor.legal_name,
        },
    )

    return vendor


@transaction.atomic
def submit_vendor_kyc_service(*, vendor: Vendor, user: User) -> Vendor:
    """
    Transitions Vendor state from DRAFT to SUBMITTED.
    """
    if vendor.status != Vendor.STATUS_DRAFT:
        raise ValidationError(f"Cannot submit vendor in status '{vendor.status}'. Must be DRAFT.")

    if not vendor.documents.exists():
        raise ValidationError(
            "At least one KYC document must be uploaded before submitting registration."
        )

    previous_status = vendor.status
    vendor.status = Vendor.STATUS_SUBMITTED
    vendor.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="Vendor",
        target_object_id=str(vendor.id),
        previous_state={"status": previous_status},
        new_state={"status": vendor.status},
    )
    return vendor


@transaction.atomic
def start_kyc_review_service(*, vendor: Vendor, reviewer: User) -> Vendor:
    """
    Transitions Vendor state to KYC_REVIEW.
    """
    if vendor.status != Vendor.STATUS_SUBMITTED:
        raise ValidationError(
            f"Cannot start KYC review for vendor in status '{vendor.status}'. Must be SUBMITTED."
        )

    previous_status = vendor.status
    vendor.status = Vendor.STATUS_KYC_REVIEW
    vendor.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=reviewer,
        action=AuditLog.ACTION_UPDATE,
        target_model="Vendor",
        target_object_id=str(vendor.id),
        previous_state={"status": previous_status},
        new_state={"status": vendor.status},
    )
    return vendor


@transaction.atomic
def verify_vendor_document_service(*, document: VendorDocument, verifier: User) -> VendorDocument:
    """
    Marks a KYC document as verified.
    """
    if document.is_verified:
        raise ValidationError("Document is already verified.")
    document.is_verified = True
    document.verified_by = verifier
    document.save(update_fields=["is_verified", "verified_by", "updated_at"])
    create_audit_log_service(
        actor=verifier,
        action=AuditLog.ACTION_VERIFY,
        target_model="VendorDocument",
        target_object_id=document.id,
        previous_state={"is_verified": False},
        new_state={"is_verified": True, "vendor": document.vendor.legal_name},
    )
    return document


@transaction.atomic
def approve_vendor_service(*, vendor: Vendor, manager: User, notes: str = "") -> Vendor:
    """
    Approves Vendor and transitions state from KYC_REVIEW to APPROVED and ACTIVE.
    """
    if vendor.status not in [Vendor.STATUS_SUBMITTED, Vendor.STATUS_KYC_REVIEW]:
        raise ValidationError(f"Cannot approve vendor in status '{vendor.status}'.")

    # Ensure documents are uploaded
    if not vendor.documents.exists():
        raise ValidationError("Cannot approve vendor with no uploaded KYC documents.")

    previous_status = vendor.status
    vendor.status = Vendor.STATUS_ACTIVE
    vendor.status_notes = notes
    vendor.save(update_fields=["status", "status_notes", "updated_at"])

    AuditLog.objects.create(
        actor=manager,
        action=AuditLog.ACTION_APPROVE,
        target_model="Vendor",
        target_object_id=str(vendor.id),
        previous_state={"status": previous_status},
        new_state={"status": vendor.status, "notes": notes},
    )
    return vendor


# (from_status, to_status) -> capability required. Anything not listed is an invalid transition.
VENDOR_GOVERNANCE_TRANSITIONS = {
    (Vendor.STATUS_ACTIVE, Vendor.STATUS_ON_HOLD): "operate",
    (Vendor.STATUS_ON_HOLD, Vendor.STATUS_ACTIVE): "operate",
    (Vendor.STATUS_ACTIVE, Vendor.STATUS_SUSPENDED): "suspend",
    (Vendor.STATUS_ON_HOLD, Vendor.STATUS_SUSPENDED): "suspend",
    (Vendor.STATUS_SUSPENDED, Vendor.STATUS_ACTIVE): "suspend",
    (Vendor.STATUS_SUBMITTED, Vendor.STATUS_REJECTED): "operate",
    (Vendor.STATUS_KYC_REVIEW, Vendor.STATUS_REJECTED): "operate",
}


def allowed_governance_transitions(vendor: Vendor, user: User) -> list:
    """Target statuses the given user may move this vendor to (drives the UI and the API)."""
    from .permissions import can_operate_governance, can_suspend_vendor

    checks = {"operate": can_operate_governance(user), "suspend": can_suspend_vendor(user)}
    return [
        to_status
        for (from_status, to_status), capability in VENDOR_GOVERNANCE_TRANSITIONS.items()
        if from_status == vendor.status and checks[capability]
    ]


@transaction.atomic
def set_vendor_status_governance_service(
    *, vendor: Vendor, actor: User, new_status: str, notes: str
) -> Vendor:
    """
    Governance status change (hold / release / suspend / reinstate / reject) through the
    VENDOR_GOVERNANCE_TRANSITIONS table. Records the vendor's open sourcing/PO exposure in the
    audit trail. Open transactions are NOT auto-cancelled (OPEN DECISION, ASSUMP-009); a
    suspended vendor is blocked from new invitations, bids, awards and POs by those services.
    """
    from .permissions import can_operate_governance, can_suspend_vendor
    from .selectors import get_vendor_open_transactions

    Vendor.objects.select_for_update().filter(pk=vendor.pk).first()
    vendor.refresh_from_db()
    if vendor.status == new_status:
        if (notes or "").strip():
            vendor.status_notes = notes.strip()
            vendor.save(update_fields=["status_notes", "updated_at"])
        return vendor
    capability = VENDOR_GOVERNANCE_TRANSITIONS.get((vendor.status, new_status))
    if capability is None:
        raise ValidationError(f"Invalid vendor status transition {vendor.status} -> {new_status}.")
    allowed = (
        can_suspend_vendor(actor) if capability == "suspend" else can_operate_governance(actor)
    )
    if not allowed:
        raise PermissionDenied(
            "Your role is not authorised to perform this vendor governance action."
        )
    if not (notes or "").strip():
        raise ValidationError("A governance reason / note is required.")

    exposure = get_vendor_open_transactions(vendor)["summary"]
    previous_status = vendor.status
    vendor.status = new_status
    vendor.status_notes = notes.strip()
    vendor.save(update_fields=["status", "status_notes", "updated_at"])

    create_audit_log_service(
        actor=actor,
        action=(
            AuditLog.ACTION_REJECT
            if new_status == Vendor.STATUS_REJECTED
            else AuditLog.ACTION_UPDATE
        ),
        target_model="Vendor",
        target_object_id=vendor.id,
        previous_state={"status": previous_status},
        new_state={
            "status": vendor.status,
            "notes": vendor.status_notes,
            "open_transactions_at_change": exposure,
        },
    )
    notify_vendor_users(
        vendor=vendor,
        notification_type=Notification.TYPE_KYC_REQUEST,
        title=f"Vendor status changed to {vendor.get_status_display()}",
        message=vendor.status_notes[:500],
        target_url="/vendor/profile/",
    )
    return vendor


@transaction.atomic
def record_vendor_risk_assessment_service(
    *, vendor: Vendor, assessor: User, risk_level: str, risk_flags: list, notes: str
) -> VendorRiskRecord:
    """Appends a new risk assessment (risk history is never overwritten)."""
    from .permissions import can_operate_governance

    if not can_operate_governance(assessor):
        raise PermissionDenied("Your role is not authorised to record vendor risk assessments.")
    valid_levels = {code for code, _ in VendorRiskRecord.RISK_CHOICES}
    if risk_level not in valid_levels:
        raise ValidationError(f"Invalid risk level '{risk_level}'.")
    valid_flags = {code for code, _ in VendorRiskRecord.RISK_FLAG_CHOICES}
    risk_flags = list(dict.fromkeys(risk_flags or []))
    unknown = [f for f in risk_flags if f not in valid_flags]
    if unknown:
        raise ValidationError(f"Unknown risk flag(s): {', '.join(unknown)}.")
    if not (notes or "").strip():
        raise ValidationError("Assessment notes are required.")

    previous = vendor.risk_records.order_by("-created_at").first()
    record = VendorRiskRecord.objects.create(
        vendor=vendor,
        risk_level=risk_level,
        risk_flags=risk_flags,
        assessment_notes=notes.strip(),
        assessed_by=assessor,
        created_by=assessor,
    )
    create_audit_log_service(
        actor=assessor,
        action=AuditLog.ACTION_CREATE,
        target_model="VendorRiskRecord",
        target_object_id=record.id,
        previous_state=(
            {"risk_level": previous.risk_level, "risk_flags": previous.risk_flags}
            if previous
            else None
        ),
        new_state={
            "vendor": vendor.legal_name,
            "risk_level": record.risk_level,
            "risk_flags": record.risk_flags,
        },
    )
    return record


@transaction.atomic
def update_vendor_profile_service(
    *,
    vendor: Vendor,
    user: User,
    data: dict,
) -> Vendor:
    """
    Vendor self-service profile update: updates trade name, address, phone, and banking info.
    Legal name, TIN, vendor number, and category are locked and require governance approval.
    """
    previous_state = {
        "trade_name": vendor.trade_name,
        "address": vendor.address,
        "phone": vendor.phone,
        "bank_name": vendor.bank_name,
        "bank_account_number": vendor.bank_account_number,
        "bank_routing_code": vendor.bank_routing_code,
    }

    if "trade_name" in data:
        vendor.trade_name = data["trade_name"]
    if "address" in data:
        vendor.address = data["address"]
    if "phone" in data:
        vendor.phone = data["phone"]
    if "bank_name" in data:
        vendor.bank_name = data["bank_name"]
    if "bank_account_number" in data:
        vendor.bank_account_number = data["bank_account_number"]
    if "bank_routing_code" in data:
        vendor.bank_routing_code = data["bank_routing_code"]

    vendor.save(
        update_fields=[
            "trade_name",
            "address",
            "phone",
            "bank_name",
            "bank_account_number",
            "bank_routing_code",
            "updated_at",
        ]
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="Vendor",
        target_object_id=str(vendor.id),
        previous_state=previous_state,
        new_state={
            "trade_name": vendor.trade_name,
            "address": vendor.address,
            "phone": vendor.phone,
            "bank_name": vendor.bank_name,
            "bank_account_number": vendor.bank_account_number,
            "bank_routing_code": vendor.bank_routing_code,
        },
    )
    return vendor


@transaction.atomic
def upload_vendor_document_service(
    *,
    vendor: Vendor,
    user: User,
    file,
    document_type: str,
    title: str = "",
    expiry_date=None,
) -> VendorDocument:
    """
    Uploads a KYC or compliance document for a vendor.
    """
    if document_type not in dict(VendorDocument.DOC_TYPE_CHOICES):
        raise ValidationError(f"Invalid document type '{document_type}'.")
    validate_file_upload(file)
    if not title or not title.strip():
        title = getattr(file, "name", "Vendor Document")

    doc = VendorDocument.objects.create(
        vendor=vendor,
        document_type=document_type,
        title=title.strip(),
        file=file,
        expiry_date=expiry_date,
        is_verified=False,
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_CREATE,
        target_model="VendorDocument",
        target_object_id=str(doc.id),
        new_state={
            "vendor": vendor.legal_name,
            "document_type": doc.document_type,
            "title": doc.title,
        },
    )
    return doc
