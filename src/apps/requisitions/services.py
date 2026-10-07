from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalAction, ApprovalPolicy
from apps.approvals.services import evaluate_approval_chain, record_approval_action_service
from apps.audit.models import AuditLog
from apps.budgets.services import (
    BudgetOverrunException,
    check_and_reserve_budget_service,
    release_budget_reservation_service,
    validate_budget_availability_service,
)
from apps.organization.models import CostCenter, Department

from .models import PRAttachment, PRLine, PurchaseRequisition


@transaction.atomic
def create_purchase_requisition_service(
    *,
    title: str,
    justification: str,
    requester: User,
    department: Department,
    cost_center: CostCenter,
    requested_delivery_date,
    line_items: list,
    attachments: list = None,
) -> PurchaseRequisition:
    """
    Creates a new PurchaseRequisition in DRAFT status with atomic document number generation.
    """
    if not line_items:
        raise ValidationError("Purchase Requisition must contain at least one line item.")

    pr_count = PurchaseRequisition.objects.count() + 1
    pr_number = f"PR-{timezone.now().strftime('%Y')}-{pr_count:05d}"

    pr = PurchaseRequisition.objects.create(
        pr_number=pr_number,
        title=title,
        justification=justification,
        requester=requester,
        department=department,
        cost_center=cost_center,
        status=PurchaseRequisition.STATUS_DRAFT,
        requested_delivery_date=requested_delivery_date,
        total_amount=Decimal("0.00"),
    )

    total = Decimal("0.00")
    for item in line_items:
        line = PRLine.objects.create(
            requisition=pr,
            item_description=item["item_description"],
            quantity=Decimal(str(item["quantity"])),
            unit_of_measure=item.get("unit_of_measure", "EA"),
            estimated_unit_price=Decimal(str(item["estimated_unit_price"])),
            specifications=item.get("specifications", ""),
        )
        total += line.estimated_total

    pr.total_amount = total

    # Validate budget availability before saving PR to prevent draft creation on overspend
    validate_budget_availability_service(
        cost_center=cost_center,
        amount=total,
        today=requested_delivery_date,
    )

    pr.save(update_fields=["total_amount", "updated_at"])

    if attachments:
        for uploaded_file in attachments:
            PRAttachment.objects.create(
                requisition=pr,
                uploaded_by=requester,
                title=uploaded_file.name,
                file=uploaded_file,
            )

    AuditLog.objects.create(
        actor=requester,
        action=AuditLog.ACTION_CREATE,
        target_model="PurchaseRequisition",
        target_object_id=str(pr.id),
        new_state={
            "pr_number": pr.pr_number,
            "total_amount": str(pr.total_amount),
            "status": pr.status,
        },
    )

    return pr


@transaction.atomic
def submit_purchase_requisition_service(
    *, requisition: PurchaseRequisition, user: User
) -> PurchaseRequisition:
    """
    Submits a PR for approval:
    1. Evaluates server-side approval chain.
    2. Runs pre-approval budget check & locks reservation.
    3. Transitions PR status to SUBMITTED / MANAGER_REVIEW.
    """
    if requisition.status != PurchaseRequisition.STATUS_DRAFT:
        raise ValidationError(
            f"Cannot submit requisition in status '{requisition.status}'. Must be DRAFT."
        )

    if requisition.total_amount <= Decimal("0.00"):
        raise ValidationError("Requisition total amount must be greater than zero.")

    # Evaluate approval policy
    evaluate_approval_chain(
        module=ApprovalPolicy.MODULE_PR,
        amount=requisition.total_amount,
        department=requisition.department,
    )

    try:
        # Execute budget reservation check
        check_and_reserve_budget_service(requisition=requisition, requested_by_user=user)
        requisition.status = PurchaseRequisition.STATUS_MANAGER_REVIEW
    except BudgetOverrunException:
        # Route to budget exception review
        requisition.status = PurchaseRequisition.STATUS_BUDGET_REVIEW

    previous_status = PurchaseRequisition.STATUS_DRAFT
    requisition.save(update_fields=["status", "updated_at"])

    record_approval_action_service(
        target_object_id=requisition.id,
        target_model_name="PurchaseRequisition",
        actor=user,
        action=ApprovalAction.ACTION_SUBMIT,
        previous_state=previous_status,
        new_state=requisition.status,
        comments="PR submitted for approval workflow.",
    )

    # Notify Department Approvers via Notification model
    from apps.accounts.models import Role, User
    from apps.notifications.models import Notification

    approvers = User.objects.filter(role__code=Role.DEPT_APPROVER)
    if requisition.department:
        dept_approvers = approvers.filter(department=requisition.department)
        if dept_approvers.exists():
            approvers = dept_approvers

    for approver in approvers:
        Notification.objects.create(
            recipient=approver,
            notification_type=Notification.TYPE_APPROVAL_REQUIRED,
            title=f"New PR Approval Request: {requisition.pr_number}",
            message=f"Requisition {requisition.pr_number} ({requisition.title}) amounting to ${requisition.total_amount} requires your department approval review.",
            target_url=f"/requisitions/{requisition.id}/",
        )

    return requisition


@transaction.atomic
def approve_purchase_requisition_service(
    *, requisition: PurchaseRequisition, approver: User, comments: str = ""
) -> PurchaseRequisition:
    """
    Approves a PR and transitions state to APPROVED.
    """
    allowed_statuses = [
        PurchaseRequisition.STATUS_SUBMITTED,
        PurchaseRequisition.STATUS_MANAGER_REVIEW,
        PurchaseRequisition.STATUS_BUDGET_REVIEW,
    ]
    if requisition.status not in allowed_statuses:
        raise ValidationError(f"Cannot approve requisition in status '{requisition.status}'.")

    previous_status = requisition.status

    if requisition.status == PurchaseRequisition.STATUS_BUDGET_REVIEW:
        # Finance is approving an overrun explicitly, force the reservation
        check_and_reserve_budget_service(
            requisition=requisition, requested_by_user=approver, force_overrun=True
        )
    elif requisition.status == PurchaseRequisition.STATUS_MANAGER_REVIEW:
        # Manager is approving. If it wasn't already reserved, reserve it now.
        # Wait, if it didn't overrun, it was reserved during submission. But we should ideally just leave it reserved.
        # However, to be safe, we just update status.
        pass

    requisition.status = PurchaseRequisition.STATUS_APPROVED
    requisition.save(update_fields=["status", "updated_at"])

    record_approval_action_service(
        target_object_id=requisition.id,
        target_model_name="PurchaseRequisition",
        actor=approver,
        action=ApprovalAction.ACTION_APPROVE,
        previous_state=previous_status,
        new_state=requisition.status,
        comments=comments or "Requisition approved.",
    )

    return requisition


@transaction.atomic
def reject_purchase_requisition_service(
    *, requisition: PurchaseRequisition, approver: User, comments: str
) -> PurchaseRequisition:
    """
    Rejects a PR and transitions state to REJECTED.
    """
    if not comments:
        raise ValidationError("Rejection justification comments are mandatory.")

    previous_status = requisition.status
    requisition.status = PurchaseRequisition.STATUS_REJECTED
    requisition.save(update_fields=["status", "updated_at"])

    # Release any active budget reservations for this requisition
    release_budget_reservation_service(
        requisition=requisition, user=approver, reason=f"PR Rejected: {comments}"
    )

    record_approval_action_service(
        target_object_id=requisition.id,
        target_model_name="PurchaseRequisition",
        actor=approver,
        action=ApprovalAction.ACTION_REJECT,
        previous_state=previous_status,
        new_state=requisition.status,
        comments=comments,
    )

    return requisition
