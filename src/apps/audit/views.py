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
    audit_logs = AuditLog.objects.all().order_by("-created_at")[:100]

    if action_filter:
        audit_logs = audit_logs.filter(action=action_filter)

    return render(
        request,
        "audit/audit_log.html",
        {
            "audit_logs": audit_logs,
            "action_filter": action_filter,
        },
    )
