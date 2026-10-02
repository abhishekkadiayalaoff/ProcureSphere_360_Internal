from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from apps.accounts.models import User, Role
from apps.organization.models import Organization, Department, CostCenter
from apps.budgets.models import Budget
from apps.approvals.models import ApprovalPolicy
from apps.audit.models import AuditLog
from apps.core.superadmin_forms import UserAdminForm, OrganizationAdminForm, BudgetAdminForm, PolicyAdminForm

@login_required
def user_list_view(request):
    users = User.objects.select_related('role', 'department').all().order_by('-date_joined')
    return render(request, "pages/dashboards/superadmin/users.html", {"users": users})

@login_required
def user_create_view(request):
    if request.method == "POST":
        form = UserAdminForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = form.cleaned_data['email']
            user.save()
            return HttpResponse('<script>window.location.reload();</script>')
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
            return HttpResponse('<script>window.location.reload();</script>')
    else:
        form = UserAdminForm(instance=user)
    return render(request, "pages/dashboards/superadmin/user_form.html", {"form": form})

@login_required
def org_list_view(request):
    orgs = Organization.objects.all()
    departments = Department.objects.select_related('organization').all()
    cost_centers = CostCenter.objects.select_related('department').all()
    return render(request, "pages/dashboards/superadmin/organizations.html", {
        "orgs": orgs, "departments": departments, "cost_centers": cost_centers
    })

@login_required
def org_create_view(request):
    if request.method == "POST":
        form = OrganizationAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('<script>window.location.reload();</script>')
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
            return HttpResponse('<script>window.location.reload();</script>')
    else:
        form = OrganizationAdminForm(instance=org)
    return render(request, "pages/dashboards/superadmin/org_form.html", {"form": form})

@login_required
def budget_list_view(request):
    budgets = Budget.objects.select_related('cost_center', 'fiscal_period').all()
    return render(request, "pages/dashboards/superadmin/budgets.html", {"budgets": budgets})

@login_required
def policy_list_view(request):
    policies = ApprovalPolicy.objects.select_related('department').all()
    return render(request, "pages/dashboards/superadmin/policies.html", {"policies": policies})

@login_required
def audit_list_view(request):
    logs = AuditLog.objects.select_related('actor').all().order_by('-timestamp')[:500]
    return render(request, "pages/dashboards/superadmin/audit.html", {"logs": logs})

@login_required
def budget_create_view(request):
    if request.method == "POST":
        form = BudgetAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('<script>window.location.reload();</script>')
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
            return HttpResponse('<script>window.location.reload();</script>')
    else:
        form = BudgetAdminForm(instance=budget)
    return render(request, "pages/dashboards/superadmin/budget_form.html", {"form": form})

@login_required
def policy_create_view(request):
    if request.method == "POST":
        form = PolicyAdminForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponse('<script>window.location.reload();</script>')
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
            return HttpResponse('<script>window.location.reload();</script>')
    else:
        form = PolicyAdminForm(instance=policy)
    return render(request, "pages/dashboards/superadmin/policy_form.html", {"form": form})
