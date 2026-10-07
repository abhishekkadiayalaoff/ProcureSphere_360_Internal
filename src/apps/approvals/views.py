from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.accounts.models import Role
from apps.requisitions.models import PurchaseRequisition

from .services import process_approval_action_service


@login_required(login_url="/login/")
def approvals_inbox_view(request):
    """
    Unified Approvals Inbox for Department Approvers, Procurement Managers, and Finance.
    """
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )

    if request.method == "POST":
        if role_code == Role.AUDITOR:
            messages.error(
                request,
                "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot approve or reject requisitions.",
            )
            return redirect("approvals_inbox")

        pr_id = request.POST.get("pr_id")
        action = request.POST.get("action")  # APPROVED or REJECTED
        comments = request.POST.get("comments", "").strip()

        try:
            pr = PurchaseRequisition.objects.get(id=pr_id)
            if action in ["REJECT", "REJECTED"] and not comments:
                comments = "Rejected by Department Approver."
            process_approval_action_service(
                target_object=pr,
                actor=request.user,
                action=action,
                comments=comments,
            )
            messages.success(request, f"Requisition {pr.pr_number} successfully {action.lower()}!")
            referer = request.META.get("HTTP_REFERER")
            if referer:
                return redirect(referer)
            return redirect("approvals_inbox")
        except Exception as e:
            messages.error(request, f"Error processing approval action: {str(e)}")

    tab = request.GET.get("tab", "pending")
    search_q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if role_code == Role.REQUESTER:
        pending_prs = PurchaseRequisition.objects.filter(
            requester=user,
            status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"],
        )
        history_prs = PurchaseRequisition.objects.filter(
            requester=user,
            status__in=["APPROVED", "REJECTED", "SOURCING", "PO_ISSUED"],
        )
    elif role_code == Role.DEPT_APPROVER:
        user_dept = getattr(user, "department", None)
        if user_dept:
            pending_prs = PurchaseRequisition.objects.filter(
                department=user_dept,
                status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"],
            )
            history_prs = PurchaseRequisition.objects.filter(
                department=user_dept,
                status__in=["APPROVED", "REJECTED", "SOURCING", "PO_ISSUED"],
            )
        else:
            pending_prs = PurchaseRequisition.objects.none()
            history_prs = PurchaseRequisition.objects.none()
    else:
        pending_prs = PurchaseRequisition.objects.filter(
            status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]
        )
        history_prs = PurchaseRequisition.objects.filter(
            status__in=["APPROVED", "REJECTED", "SOURCING", "PO_ISSUED"]
        )

    if search_q:
        q_filter = (
            Q(pr_number__icontains=search_q)
            | Q(title__icontains=search_q)
            | Q(requester__email__icontains=search_q)
            | Q(department__name__icontains=search_q)
        )
        pending_prs = pending_prs.filter(q_filter)
        history_prs = history_prs.filter(q_filter)

    if status_filter:
        pending_prs = pending_prs.filter(status=status_filter)
        history_prs = history_prs.filter(status=status_filter)

    pending_prs = pending_prs.order_by("-updated_at")
    history_prs = history_prs.order_by("-updated_at")

    if role_code == Role.LEGAL_MGR or role_code == "LEGAL_MGR":
        base_layout = "layouts/legal_base.html"
    elif role_code in [Role.DEPT_APPROVER, Role.PROC_MGR]:
        base_layout = "layouts/approver_base.html"
    else:
        base_layout = "layouts/requester_base.html"

    context = {
        "pending_prs": pending_prs,
        "history_prs": history_prs,
        "active_tab": tab,
        "role_code": role_code,
        "base_layout": base_layout,
        "search_q": search_q,
        "status_filter": status_filter,
    }
    return render(request, "pages/approvals/inbox.html", context)


# Alias for URL route compatibility
inbox_view = approvals_inbox_view
