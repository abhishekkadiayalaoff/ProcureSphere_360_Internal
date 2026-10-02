from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.vendors.models import Vendor

from .models import (
    Contract,
    ContractAlert,
    ContractDocument,
    ContractMilestone,
    ContractObligation,
    ContractVersion,
)


@transaction.atomic
def create_contract_service(
    *,
    title: str,
    vendor: Vendor,
    contract_value: Decimal,
    start_date,
    end_date,
    contract_owner: User,
    renewal_notice_days: int = 30,
    sourcing_event=None,
    po=None,
) -> Contract:
    """
    Creates a new Contract in DRAFT status.
    """
    contract_count = Contract.objects.count() + 1
    contract_number = f"CON-{timezone.now().strftime('%Y')}-{contract_count:05d}"

    contract = Contract.objects.create(
        contract_number=contract_number,
        title=title,
        version=1,
        vendor=vendor,
        sourcing_event=sourcing_event,
        po=po,
        status=Contract.STATUS_DRAFT,
        contract_value=contract_value,
        start_date=start_date,
        end_date=end_date,
        renewal_notice_days=renewal_notice_days,
        contract_owner=contract_owner,
    )

    # Initial Version 1 Snapshot
    ContractVersion.objects.create(
        contract=contract,
        version_number=1,
        amendment_summary="Initial Contract Execution Draft",
        contract_value=contract_value,
        start_date=start_date,
        end_date=end_date,
        approved_by=contract_owner,
    )

    AuditLog.objects.create(
        actor=contract_owner,
        action=AuditLog.ACTION_CREATE,
        target_model="Contract",
        target_object_id=str(contract.id),
        new_state={
            "contract_number": contract.contract_number,
            "vendor": vendor.legal_name,
            "value": str(contract_value),
            "status": contract.status,
        },
    )

    return contract


@transaction.atomic
def submit_for_legal_review_service(*, contract: Contract, user: User, notes: str = "") -> Contract:
    """
    Submits contract from DRAFT to LEGAL_REVIEW state.
    """
    if contract.status != Contract.STATUS_DRAFT:
        raise ValidationError(f"Cannot submit contract in status '{contract.status}' for legal review.")

    previous_status = contract.status
    contract.status = Contract.STATUS_LEGAL_REVIEW
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": contract.status, "notes": notes},
    )

    return contract


@transaction.atomic
def approve_legal_review_service(*, contract: Contract, user: User, notes: str = "") -> Contract:
    """
    Approves legal review, moving contract to BUSINESS_APPROVAL state.
    """
    if contract.status != Contract.STATUS_LEGAL_REVIEW:
        raise ValidationError(f"Cannot perform legal approval on contract in status '{contract.status}'.")

    previous_status = contract.status
    contract.status = Contract.STATUS_BUSINESS_APPROVAL
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_APPROVE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": contract.status, "legal_approval_notes": notes},
    )

    return contract


@transaction.atomic
def reject_legal_review_service(*, contract: Contract, user: User, reason: str) -> Contract:
    """
    Rejects legal review, returning contract to DRAFT state for corrections.
    """
    if contract.status != Contract.STATUS_LEGAL_REVIEW:
        raise ValidationError(f"Cannot reject legal review for contract in status '{contract.status}'.")

    previous_status = contract.status
    contract.status = Contract.STATUS_DRAFT
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_REJECT,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": contract.status, "rejection_reason": reason},
    )

    return contract


@transaction.atomic
def approve_business_service(*, contract: Contract, user: User, notes: str = "") -> Contract:
    """
    Business owner approves contract, moving status from BUSINESS_APPROVAL to ACTIVE.
    """
    if contract.status not in [Contract.STATUS_BUSINESS_APPROVAL, Contract.STATUS_LEGAL_REVIEW, Contract.STATUS_DRAFT]:
        raise ValidationError(f"Cannot perform business approval on contract in status '{contract.status}'.")

    previous_status = contract.status
    contract.status = Contract.STATUS_ACTIVE
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_APPROVE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": contract.status, "business_approval_notes": notes},
    )

    return contract


@transaction.atomic
def activate_contract_service(*, contract: Contract, user: User) -> Contract:
    """
    Activates contract state from DRAFT / LEGAL_REVIEW to ACTIVE directly.
    """
    previous_status = contract.status
    contract.status = Contract.STATUS_ACTIVE
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_APPROVE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": contract.status},
    )

    return contract


@transaction.atomic
def create_contract_version_service(
    *,
    contract: Contract,
    user: User,
    amendment_summary: str,
    contract_value: Decimal,
    start_date,
    end_date,
) -> ContractVersion:
    """
    Amends contract by incrementing version number, preserving prior version values,
    and updating active contract values.
    """
    new_version_number = contract.version + 1

    # Record historic version snapshot
    version_record = ContractVersion.objects.create(
        contract=contract,
        version_number=new_version_number,
        amendment_summary=amendment_summary,
        contract_value=contract_value,
        start_date=start_date,
        end_date=end_date,
        approved_by=user,
    )

    # Update active Contract instance
    contract.version = new_version_number
    contract.contract_value = contract_value
    contract.start_date = start_date
    contract.end_date = end_date
    contract.save(update_fields=["version", "contract_value", "start_date", "end_date", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="Contract",
        target_object_id=str(contract.id),
        new_state={
            "version": new_version_number,
            "amendment_summary": amendment_summary,
            "contract_value": str(contract_value),
        },
    )

    return version_record


@transaction.atomic
def add_contract_milestone_service(
    *, contract: Contract, title: str, due_date, amount: Decimal = Decimal("0.00")
) -> ContractMilestone:
    """
    Adds a tracked milestone to a contract.
    """
    milestone = ContractMilestone.objects.create(
        contract=contract,
        title=title,
        due_date=due_date,
        amount=amount,
    )
    return milestone


@transaction.atomic
def complete_contract_milestone_service(*, milestone: ContractMilestone, user: User) -> ContractMilestone:
    """
    Marks a milestone as completed.
    """
    milestone.is_completed = True
    milestone.completed_at = timezone.now()
    milestone.save(update_fields=["is_completed", "completed_at", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="ContractMilestone",
        target_object_id=str(milestone.id),
        new_state={"title": milestone.title, "is_completed": True},
    )

    return milestone


@transaction.atomic
def add_contract_obligation_service(
    *, contract: Contract, title: str, responsible_party: str, due_date
) -> ContractObligation:
    """
    Adds a legal obligation to a contract.
    """
    obligation = ContractObligation.objects.create(
        contract=contract,
        title=title,
        responsible_party=responsible_party,
        due_date=due_date,
    )
    return obligation


@transaction.atomic
def fulfill_contract_obligation_service(*, obligation: ContractObligation, user: User) -> ContractObligation:
    """
    Marks an obligation as fulfilled.
    """
    obligation.is_fulfilled = True
    obligation.fulfilled_at = timezone.now()
    obligation.save(update_fields=["is_fulfilled", "fulfilled_at", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="ContractObligation",
        target_object_id=str(obligation.id),
        new_state={"title": obligation.title, "is_fulfilled": True},
    )

    return obligation


@transaction.atomic
def upload_contract_document_service(
    *, contract: Contract, user: User, title: str, file
) -> ContractDocument:
    """
    Uploads a signed contract document or appendix.
    """
    document = ContractDocument.objects.create(
        contract=contract,
        title=title,
        file=file,
        uploaded_by=user,
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_CREATE,
        target_model="ContractDocument",
        target_object_id=str(document.id),
        new_state={"title": title, "file_name": str(file)},
    )

    return document


@transaction.atomic
def renew_contract_service(
    *, contract: Contract, user: User, new_end_date, new_value: Decimal = None, notes: str = ""
) -> Contract:
    """
    Renews an active or renewal-due contract, creating a new version.
    """
    if contract.status not in [Contract.STATUS_ACTIVE, Contract.STATUS_RENEWAL_DUE, Contract.STATUS_EXPIRED]:
        raise ValidationError(f"Cannot renew contract in status '{contract.status}'.")

    value = new_value if new_value is not None else contract.contract_value
    previous_status = contract.status
    contract.status = Contract.STATUS_RENEWED
    contract.end_date = new_end_date
    contract.contract_value = value
    contract.save(update_fields=["status", "end_date", "contract_value", "updated_at"])

    create_contract_version_service(
        contract=contract,
        user=user,
        amendment_summary=f"Contract Renewal Extension to {new_end_date}. {notes}".strip(),
        contract_value=value,
        start_date=contract.start_date,
        end_date=new_end_date,
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_APPROVE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status, "end_date": str(contract.end_date)},
        new_state={"status": contract.status, "new_end_date": str(new_end_date), "value": str(value)},
    )

    return contract


@transaction.atomic
def terminate_contract_service(*, contract: Contract, user: User, reason: str) -> Contract:
    """
    Terminates a contract.
    """
    if contract.status == Contract.STATUS_TERMINATED:
        raise ValidationError("Contract is already terminated.")

    previous_status = contract.status
    contract.status = Contract.STATUS_TERMINATED
    contract.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="Contract",
        target_object_id=str(contract.id),
        previous_state={"status": previous_status},
        new_state={"status": Contract.STATUS_TERMINATED, "reason": reason},
    )

    return contract


@transaction.atomic
def scan_contract_expirations_and_milestones_service() -> int:
    """
    Scans active contracts for upcoming expirations & milestones.
    Executes scheduled Celery Beat task logic and logs alerts.
    Returns count of generated alerts.
    """
    today = timezone.now().date()
    alerts_created = 0

    # 1. Expiration scan
    active_contracts = Contract.objects.filter(status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_RENEWED])
    for contract in active_contracts:
        notice_date = contract.end_date - timezone.timedelta(days=contract.renewal_notice_days)
        if (
            today >= notice_date
            and not ContractAlert.objects.filter(
                contract=contract, alert_type=ContractAlert.ALERT_RENEWAL
            ).exists()
        ):
            ContractAlert.objects.create(
                contract=contract,
                alert_type=ContractAlert.ALERT_RENEWAL,
                message=f"Contract '{contract.contract_number}' is reaching renewal notice period (End date: {contract.end_date}).",
            )
            contract.status = Contract.STATUS_RENEWAL_DUE
            contract.save(update_fields=["status", "updated_at"])
            alerts_created += 1

    # 2. Milestone due scan
    pending_milestones = ContractMilestone.objects.select_related("contract").filter(
        is_completed=False, due_date__lte=today + timezone.timedelta(days=7)
    )
    for milestone in pending_milestones:
        if not ContractAlert.objects.filter(
            contract=milestone.contract,
            alert_type=ContractAlert.ALERT_MILESTONE,
            message__contains=milestone.title,
        ).exists():
            ContractAlert.objects.create(
                contract=milestone.contract,
                alert_type=ContractAlert.ALERT_MILESTONE,
                message=f"Milestone '{milestone.title}' for contract '{milestone.contract.contract_number}' is due on {milestone.due_date}.",
            )
            alerts_created += 1

    return alerts_created
