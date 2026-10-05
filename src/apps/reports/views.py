from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.reports.models import ExportJob
from apps.reports.services import generate_export_job_service


@login_required(login_url="/login/")
def dashboard_view(request):
    jobs = ExportJob.objects.filter(requested_by=request.user).order_by("-created_at")[:20]

    reports = [
        {"id": "spend_analytics", "name": "Spend Analytics", "desc": "Spend by cost center and period"},
        {"id": "pr_aging", "name": "PR Approval Aging", "desc": "Requisition cycle times and pending approver bottlenecks"},
        {"id": "sourcing_cycle", "name": "Sourcing Cycle Time", "desc": "RFQ/RFP duration and supplier participation"},
        {"id": "invoice_exception_aging", "name": "Match Exception Aging", "desc": "Aging report of open 3-way match exceptions"},
        {"id": "contract_expiry", "name": "Contract Expiry Pipeline", "desc": "Upcoming contract expirations within 30/60/90 days"},
        {"id": "supplier_scorecard", "name": "Supplier Scorecard Export", "desc": "Comprehensive weighted scorecards for vendor review"},
    ]

    return render(
        request,
        "pages/reports/dashboard.html",
        {"jobs": jobs, "reports": reports}
    )


# Aliases so both URL names work
reports_hub_view = dashboard_view


@login_required(login_url="/login/")
def generate_view(request):
    if request.method == "POST":
        report_type = request.POST.get("report_type")
        format_type = request.POST.get("format_type", "CSV")

        job = ExportJob.objects.create(
            report_type=report_type,
            export_format=format_type,
            requested_by=request.user
        )

        try:
            generate_export_job_service(job.id)
            messages.success(request, f"{report_type} report successfully generated!")
        except Exception as e:
            messages.error(request, f"Error generating report: {str(e)}")

    return redirect("reports_hub")
