from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.reports.models import ExportJob
from apps.reports.services import generate_export_job_service


@login_required(login_url="/login/")
def reports_hub_view(request):
    """
    Analytics Reports Hub & Audited Export Generator view.
    """
    export_jobs = ExportJob.objects.filter(requested_by=request.user).order_by("-created_at")[:15]

    reports_catalog = [
        {
            "id": "spend_by_category",
            "title": "Spend by Category & Department",
            "desc": "Aggregated spend breakdown across cost centers and categories.",
            "icon": "fa-chart-pie",
            "color": "primary",
        },
        {
            "id": "pr_aging",
            "title": "PR Approval Aging & Bottlenecks",
            "desc": "Requisition cycle times and pending approver bottlenecks.",
            "icon": "fa-clock",
            "color": "warning",
        },
        {
            "id": "sourcing_cycle",
            "title": "Sourcing Cycle Time & Bid Metrics",
            "desc": "RFQ/RFP duration and supplier participation statistics.",
            "icon": "fa-gavel",
            "color": "info",
        },
        {
            "id": "invoice_aging",
            "title": "Invoice Match Exception Aging",
            "desc": "Open AP match exceptions and price variance aging.",
            "icon": "fa-receipt",
            "color": "danger",
        },
        {
            "id": "contract_expiry",
            "title": "Contract Expiry & Renewal Pipeline",
            "desc": "Upcoming contract expirations within 30/60/90 days.",
            "icon": "fa-file-contract",
            "color": "dark",
        },
        {
            "id": "supplier_scorecard",
            "title": "Supplier Performance Scorecard Export",
            "desc": "Comprehensive weighted scorecards export for vendor review.",
            "icon": "fa-award",
            "color": "success",
        },
    ]

    try:
        return render(
            request,
            "reports/reports_hub.html",
            {
                "reports_catalog": reports_catalog,
                "export_jobs": export_jobs,
            },
        )
    except Exception:
        return render(
            request,
            "pages/reports/dashboard.html",
            {
                "reports": reports_catalog,
                "jobs": export_jobs,
            },
        )


dashboard_view = reports_hub_view


@login_required(login_url="/login/")
def generate_view(request):
    if request.method == "POST":
        report_type = request.POST.get("report_type", "spend_analytics")
        format_type = request.POST.get("format_type", "CSV")

        job = ExportJob.objects.create(
            report_type=report_type,
            export_format=format_type,
            requested_by=request.user,
        )

        try:
            generate_export_job_service(job.id)
            messages.success(request, f"{report_type} report successfully generated!")
        except Exception as e:
            messages.error(request, f"Error generating report: {str(e)}")

    return redirect("reports_hub")
