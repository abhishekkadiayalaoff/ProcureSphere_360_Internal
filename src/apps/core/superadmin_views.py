import csv

import openpyxl
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.accounts.models import User
from apps.approvals.models import ApprovalPolicy
from apps.audit.models import AuditLog
from apps.budgets.models import Budget
from apps.core.superadmin_forms import (
    BudgetAdminForm,
    OrganizationAdminForm,
    PolicyAdminForm,
    UserAdminForm,
)
from apps.organization.models import CostCenter, Department, Organization


@login_required
def user_list_view(request):
    users = User.objects.select_related("role", "department").all().order_by("-date_joined")
    return render(request, "pages/dashboards/superadmin/users.html", {"users": users})


@login_required
def user_create_view(request):
    if request.method == "POST":
        form = UserAdminForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data["email"]
            user.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = UserAdminForm()
    return render(request, "pages/dashboards/superadmin/user_form.html", {"form": form})


@login_required
def user_edit_view(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == "POST":
        form = UserAdminForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = UserAdminForm(instance=user)
    return render(request, "pages/dashboards/superadmin/user_form.html", {"form": form})


@login_required
def org_list_view(request):
    orgs = Organization.objects.all()
    departments = Department.objects.select_related("organization").all()
    cost_centers = CostCenter.objects.select_related("department").all()
    return render(
        request,
        "pages/dashboards/superadmin/organizations.html",
        {"orgs": orgs, "departments": departments, "cost_centers": cost_centers},
    )


@login_required
def org_create_view(request):
    if request.method == "POST":
        form = OrganizationAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = OrganizationAdminForm()
    return render(request, "pages/dashboards/superadmin/org_form.html", {"form": form})


@login_required
def org_edit_view(request, org_id):
    org = get_object_or_404(Organization, pk=org_id)
    if request.method == "POST":
        form = OrganizationAdminForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = OrganizationAdminForm(instance=org)
    return render(request, "pages/dashboards/superadmin/org_form.html", {"form": form})


@login_required
def budget_list_view(request):
    budgets = Budget.objects.select_related("cost_center", "fiscal_period").all()
    return render(request, "pages/dashboards/superadmin/budgets.html", {"budgets": budgets})


@login_required
def policy_list_view(request):
    policies = ApprovalPolicy.objects.select_related("department").all()
    return render(request, "pages/dashboards/superadmin/policies.html", {"policies": policies})


from django.core.paginator import Paginator


@login_required
def audit_list_view(request):
    logs_list = AuditLog.objects.select_related("actor").all().order_by("-timestamp")
    paginator = Paginator(logs_list, 10)  # Show 10 logs per page

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "pages/dashboards/superadmin/audit.html", {"page_obj": page_obj})


@login_required
def budget_create_view(request):
    if request.method == "POST":
        form = BudgetAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = BudgetAdminForm()
    return render(request, "pages/dashboards/superadmin/budget_form.html", {"form": form})


@login_required
def budget_edit_view(request, budget_id):
    budget = get_object_or_404(Budget, pk=budget_id)
    if request.method == "POST":
        form = BudgetAdminForm(request.POST, instance=budget)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = BudgetAdminForm(instance=budget)
    return render(request, "pages/dashboards/superadmin/budget_form.html", {"form": form})


@login_required
def policy_create_view(request):
    if request.method == "POST":
        form = PolicyAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = PolicyAdminForm()
    return render(request, "pages/dashboards/superadmin/policy_form.html", {"form": form})


@login_required
def policy_edit_view(request, policy_id):
    policy = get_object_or_404(ApprovalPolicy, pk=policy_id)
    if request.method == "POST":
        form = PolicyAdminForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            return HttpResponse("<script>window.location.reload();</script>")
    else:
        form = PolicyAdminForm(instance=policy)
    return render(request, "pages/dashboards/superadmin/policy_form.html", {"form": form})


@login_required
def audit_export_view(request):
    format_type = request.GET.get("format", "csv")
    logs = AuditLog.objects.select_related("actor").all().order_by("-timestamp")

    if format_type == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit_history.csv"'
        writer = csv.writer(response)
        writer.writerow(["Timestamp", "Actor", "Action", "Target Object", "IP Address", "Comments"])
        for log in logs:
            actor = log.actor.email if log.actor else "System"
            writer.writerow(
                [
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    actor,
                    log.action,
                    log.readable_target,
                    log.ip_address or "-",
                    getattr(log, "comments", "-") or "-",
                ]
            )
        return response

    elif format_type == "xlsx":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="audit_history.xlsx"'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Audit History"
        ws.append(["Timestamp", "Actor", "Action", "Target Object", "IP Address", "Comments"])
        for log in logs:
            actor = log.actor.email if log.actor else "System"
            ws.append(
                [
                    log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    actor,
                    log.action,
                    log.readable_target,
                    log.ip_address or "-",
                    getattr(log, "comments", "-") or "-",
                ]
            )
        wb.save(response)
        return response

    elif format_type == "pdf":
        try:
            from reportlab.pdfgen import canvas
        except ImportError:
            return HttpResponse(
                "PDF export is unavailable: reportlab is not installed.", status=501
            )
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="audit_history.pdf"'
        p = canvas.Canvas(response)
        y = 800
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, y, "ProcureSphere 360 - Audit History")
        y -= 30
        p.setFont("Helvetica", 10)

        for log in logs[:100]:  # Limit to 100 for simple PDF layout
            if y < 50:
                p.showPage()
                p.setFont("Helvetica", 10)
                y = 800

            actor = log.actor.email if log.actor else "System"
            line = f"{log.timestamp.strftime('%Y-%m-%d %H:%M')} | {actor} | {log.action} | {log.target_model} #{log.target_object_id}"
            p.drawString(50, y, line)
            y -= 15

        p.showPage()
        p.save()
        return response

    return HttpResponse("Invalid format", status=400)
