from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render

from apps.accounts.models import Role
from apps.audit.selectors import (
    get_approval_history_audit,
    get_audit_logs,
    get_audit_metrics,
    get_auditor_dashboard_data,
    get_contract_changes_audit,
    get_invoice_exceptions_audit,
    get_po_changes_audit,
    get_security_events_audit,
    get_sourcing_activity_audit,
    get_vendor_compliance_audit,
)
from apps.audit.services import get_transaction_lifecycle_service


def _enforce_auditor_access(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (user.role.code if getattr(user, "role", None) else None)
    if not (user.is_superuser or role_code in [Role.AUDITOR, Role.SUPER_ADMIN, "AUDITOR", "SUPER_ADMIN"]):
        raise PermissionDenied("Access restricted to Compliance Auditor role.")


@login_required
def auditor_dashboard_view(request):
    """
    Main Executive Compliance Auditor & Traceability Hub Dashboard.
    Supplies core executive KPIs, activity trend charts, action distribution,
    open anomalies, and recent audit activity feed.
    """
    _enforce_auditor_access(request)
    period_days = int(request.GET.get("period_days", 30))
    dashboard_data = get_auditor_dashboard_data(period_days=period_days)
    vendor_compliance = get_vendor_compliance_audit(limit=10)
    approval_history = get_approval_history_audit(limit=10)
    po_changes = get_po_changes_audit(limit=10)
    invoice_exceptions = get_invoice_exceptions_audit(limit=10)
    contract_changes = get_contract_changes_audit(limit=10)
    security_events = get_security_events_audit(limit=10)
    sourcing_activity = get_sourcing_activity_audit(limit=10)

    context = {
        "metrics": {
            "total_audit_logs": dashboard_data["metrics"]["total_logs_all_time"],
            "total_approvals": dashboard_data["metrics"]["critical_events"]["approvals"],
            "total_rejections": dashboard_data["metrics"]["critical_events"]["rejections"],
            "total_logins": dashboard_data["metrics"]["critical_events"]["logins"],
            "total_exports": dashboard_data["metrics"]["critical_events"]["exports"],
            "open_exceptions": dashboard_data["domain_counts"]["open_exceptions_count"],
            "suspended_vendors": dashboard_data["domain_counts"]["suspended_vendors_count"],
            "overdue_obligations": dashboard_data["domain_counts"]["overdue_obligations_count"],
            "compliance_rate": vendor_compliance["summary"]["compliance_rate"],
        },
        "audit_data": dashboard_data,
        "recent_logs": dashboard_data["recent_logs"],
        "recent_approvals": dashboard_data["recent_approvals"],
        "open_exceptions": dashboard_data["open_exceptions"],
        "suspended_vendors": dashboard_data["suspended_vendors"],
        "overdue_obligations": dashboard_data["overdue_obligations"],
        "active_contract_alerts": dashboard_data["active_contract_alerts"],
        "vendor_compliance": vendor_compliance,
        "approval_history": approval_history,
        "po_changes": po_changes,
        "invoice_exceptions": invoice_exceptions,
        "contract_changes": contract_changes,
        "security_events": security_events,
        "sourcing_activity": sourcing_activity,
        "period_days": period_days,
    }
    return render(request, "pages/dashboards/auditor_dashboard.html", context)


@login_required
def audit_log_view(request):
    """
    Dedicated Append-Only Immutable Audit Log Register Page.
    """
    _enforce_auditor_access(request)
    action_filter = request.GET.get("action", "").strip()
    search_query = request.GET.get("q", "").strip() or request.GET.get("search", "").strip()
    model_filter = request.GET.get("model", "").strip() or request.GET.get("target_model", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_audit_logs(
        action=action_filter or None,
        target_model=model_filter or None,
        search_term=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/logs.html",
        {
            "audit_logs": result["logs"],
            "total_count": result["total_count"],
            "action_filter": action_filter,
            "search_query": search_query,
            "model_filter": model_filter,
            "current_page": page,
            "total_pages": total_pages,
            "limit": limit,
        },
    )


@login_required
def audit_vendors_view(request):
    """
    Dedicated Vendor Compliance & KYC Audit Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_vendor_compliance_audit(
        status=status_filter or None,
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/vendors.html",
        {
            "vendors": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "status_filter": status_filter,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_approvals_view(request):
    """
    Dedicated Approval Governance History & Electronic Signature Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    action_filter = request.GET.get("action", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_approval_history_audit(
        action=action_filter or None,
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/approvals.html",
        {
            "approvals": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "action_filter": action_filter,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_po_changes_view(request):
    """
    Dedicated Purchase Order Changes & Amendments Audit Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_po_changes_audit(
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/po_changes.html",
        {
            "pos": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_invoice_exceptions_view(request):
    """
    Dedicated 3-Way Match Exception Register Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    status_filter = request.GET.get("status", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_invoice_exceptions_audit(
        status=status_filter or None,
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/invoice_exceptions.html",
        {
            "exceptions": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "status_filter": status_filter,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_contract_changes_view(request):
    """
    Dedicated Contract Compliance & Milestone SLA Risk Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_contract_changes_audit(
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/contract_changes.html",
        {
            "contracts": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_security_events_view(request):
    """
    Dedicated Security & Authentication Events Audit Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_security_events_audit(
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/security_events.html",
        {
            "security_events": result["results"],
            "summary": result["summary"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_sourcing_activity_view(request):
    """
    Dedicated Sourcing & Bids Activity Audit Page.
    """
    _enforce_auditor_access(request)
    search_query = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 50))
    offset = (page - 1) * limit

    result = get_sourcing_activity_audit(
        search=search_query or None,
        limit=limit,
        offset=offset,
    )

    total_pages = (result["total_count"] + limit - 1) // limit if result["total_count"] > 0 else 1

    return render(
        request,
        "audit/sourcing_activity.html",
        {
            "events": result["results"],
            "total_count": result["total_count"],
            "search_query": search_query,
            "current_page": page,
            "total_pages": total_pages,
        },
    )


@login_required
def audit_lifecycle_view(request):
    """
    Dedicated Lifecycle Traceability Explorer for Compliance Auditors.
    Visualizes end-to-end graph from Requisition through Payment & Contract.
    """
    _enforce_auditor_access(request)
    identifier = request.GET.get("identifier", "").strip()
    entity_type = request.GET.get("entity_type", "AUTO").strip()
    lifecycle_data = None

    if identifier:
        lifecycle_data = get_transaction_lifecycle_service(
            entity_type=entity_type,
            entity_identifier=identifier,
        )

    return render(
        request,
        "audit/lifecycle_viewer.html",
        {
            "identifier": identifier,
            "entity_type": entity_type,
            "lifecycle": lifecycle_data,
        },
    )


@login_required
def audit_metrics_api_view(request):
    """
    Statistical metrics endpoint for audit trend visualizations.
    """
    _enforce_auditor_access(request)
    period_days = int(request.GET.get("period_days", 30))
    metrics = get_audit_metrics(period_days=period_days)
    return JsonResponse(metrics)
