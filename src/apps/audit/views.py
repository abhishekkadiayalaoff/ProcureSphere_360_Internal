from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import AuditLog


@login_required
def audit_log_view(request):
    """
    Append-Only Immutable Audit Log Trail Viewer.
    """
    action_filter = request.GET.get("action", "")
    audit_logs = AuditLog.objects.all().order_by("-timestamp")[:100]

    if action_filter:
        audit_logs = audit_logs.filter(action=action_filter)

    user = request.user
    role_code = getattr(user, "role_code", "SUPER_ADMIN")
    if role_code == "DEPT_APPROVER":
        base_layout = "layouts/approver_base.html"
    elif role_code == "REQUESTER":
        base_layout = "layouts/requester_base.html"
    elif role_code in ["FINANCE_AP", "FINANCE"]:
        base_layout = "layouts/finance_base.html"
    elif role_code == "VENDOR_USER":
        base_layout = "layouts/vendor_base.html"
    elif role_code in ["SUPER_ADMIN", "ADMIN"]:
        base_layout = "layouts/superadmin_base.html"
    else:
        base_layout = "base.html"

    return render(
        request,
        "audit/audit_log.html",
        {
            "audit_logs": audit_logs,
            "action_filter": action_filter,
            "base_layout": base_layout,
        },
    )
