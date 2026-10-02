from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.accounts.models import Role
from apps.requisitions.models import PurchaseRequisition
from apps.approvals.models import ApprovalAction

@login_required(login_url="/login/")
def inbox_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN)
    
    if role_code == Role.REQUESTER:
        # Requesters don't approve things, but they can see their pending items.
        pending_prs = PurchaseRequisition.objects.filter(
            requester=user, 
            status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]
        ).order_by("-updated_at")
        
        return render(
            request,
            "pages/approvals/inbox.html",
            {
                "pending_prs": pending_prs,
                "role_code": role_code
            }
        )
    else:
        # Other roles (like DEPT_APPROVER) would see items assigned to them.
        # For now, just show all pending PRs as a placeholder.
        pending_prs = PurchaseRequisition.objects.filter(
            status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]
        ).order_by("-updated_at")
        
        return render(
            request,
            "pages/approvals/inbox.html",
            {
                "pending_prs": pending_prs,
                "role_code": role_code
            }
        )
