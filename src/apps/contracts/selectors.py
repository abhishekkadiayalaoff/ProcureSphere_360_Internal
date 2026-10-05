from django.db.models import Q, Sum
from django.utils import timezone

from apps.accounts.models import Role

from .models import Contract, ContractAlert, ContractMilestone, ContractObligation


def get_contracts_qs(user=None, status=None, search=None):
    """
    Returns filtered and scoped contracts QuerySet.
    """
    qs = Contract.objects.select_related(
        "vendor", "contract_owner", "sourcing_event", "po"
    ).prefetch_related("milestones", "obligations", "documents", "alerts", "versions")

    if user:
        role_code = getattr(user, "role_code", None) or (
            user.role.code if getattr(user, "role", None) else None
        )
        if role_code == Role.VENDOR_USER:
            vendor = getattr(user, "vendor", None)
            qs = qs.filter(vendor=vendor) if vendor else qs.none()

    if status:
        qs = qs.filter(status=status)

    if search:
        qs = qs.filter(
            Q(contract_number__icontains=search)
            | Q(title__icontains=search)
            | Q(vendor__legal_name__icontains=search)
        )

    return qs.order_by("-created_at")


def get_all_contracts():
    return get_contracts_qs()


def get_contract_by_id(contract_id):
    return (
        Contract.objects.select_related("vendor", "contract_owner", "sourcing_event", "po")
        .prefetch_related(
            "milestones",
            "obligations",
            "documents",
            "alerts",
            "versions",
            "versions__approved_by",
            "documents__uploaded_by",
        )
        .filter(id=contract_id)
        .first()
    )


def get_contracts_pending_legal_review():
    return get_contracts_qs(status=Contract.STATUS_LEGAL_REVIEW)


def get_expiring_contracts(days=30):
    today = timezone.now().date()
    future_date = today + timezone.timedelta(days=days)
    return (
        Contract.objects.select_related("vendor", "contract_owner")
        .filter(
            status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_RENEWAL_DUE],
            end_date__lte=future_date,
        )
        .order_by("end_date")
    )


def get_pending_obligations():
    return (
        ContractObligation.objects.select_related("contract", "contract__vendor")
        .filter(is_fulfilled=False)
        .order_by("due_date")
    )


def get_pending_milestones():
    return (
        ContractMilestone.objects.select_related("contract", "contract__vendor")
        .filter(is_completed=False)
        .order_by("due_date")
    )


def get_active_contract_alerts():
    return (
        ContractAlert.objects.select_related("contract", "contract__vendor")
        .filter(is_processed=False)
        .order_by("-triggered_at")
    )


def get_legal_dashboard_metrics():
    today = timezone.now().date()
    total_contracts = Contract.objects.count()
    active_contracts = Contract.objects.filter(
        status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_RENEWED]
    ).count()
    pending_legal_review = Contract.objects.filter(status=Contract.STATUS_LEGAL_REVIEW).count()
    expiring_soon = Contract.objects.filter(
        status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_RENEWAL_DUE],
        end_date__lte=today + timezone.timedelta(days=30),
    ).count()

    total_value = Contract.objects.aggregate(total=Sum("contract_value"))["total"] or 0
    open_obligations = ContractObligation.objects.filter(is_fulfilled=False).count()
    open_milestones = ContractMilestone.objects.filter(is_completed=False).count()

    return {
        "total_contracts": total_contracts,
        "active_contracts": active_contracts,
        "pending_legal_review": pending_legal_review,
        "expiring_soon": expiring_soon,
        "total_contract_value": float(total_value),
        "open_obligations": open_obligations,
        "open_milestones": open_milestones,
    }
