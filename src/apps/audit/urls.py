from django.urls import path

from .views import (
    audit_approvals_view,
    audit_contract_changes_view,
    audit_invoice_exceptions_view,
    audit_lifecycle_view,
    audit_log_view,
    audit_metrics_api_view,
    audit_po_changes_view,
    audit_security_events_view,
    audit_sourcing_activity_view,
    audit_vendors_view,
    auditor_dashboard_view,
)

urlpatterns = [
    # Main Executive Dashboard
    path("audit/", auditor_dashboard_view, name="auditor_dashboard_hub"),
    path("audit/dashboard/", auditor_dashboard_view, name="auditor_dashboard"),
    
    # Dedicated Sub-Module Pages
    path("audit/logs/", audit_log_view, name="audit_log"),
    path("audit/vendors/", audit_vendors_view, name="audit_vendors"),
    path("audit/approvals/", audit_approvals_view, name="audit_approvals"),
    path("audit/po-changes/", audit_po_changes_view, name="audit_po_changes"),
    path("audit/invoice-exceptions/", audit_invoice_exceptions_view, name="audit_invoice_exceptions"),
    path("audit/contract-changes/", audit_contract_changes_view, name="audit_contract_changes"),
    path("audit/security-events/", audit_security_events_view, name="audit_security_events"),
    path("audit/sourcing-activity/", audit_sourcing_activity_view, name="audit_sourcing_activity"),
    path("audit/lifecycle/", audit_lifecycle_view, name="audit_lifecycle"),
    path("audit/metrics/", audit_metrics_api_view, name="audit_metrics"),
]
