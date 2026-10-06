from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.budgets.models import Budget, SpendLedger
from apps.requisitions.models import PurchaseRequisition


@login_required(login_url="/login/")
def list_view(request):
    budgets = Budget.objects.select_related("cost_center", "fiscal_period").all()
    return render(request, "pages/budgets/list.html", {"budgets": budgets})


@login_required(login_url="/login/")
def ledger_view(request):
    ledger = SpendLedger.objects.select_related("budget__cost_center").order_by("-created_at")
    return render(request, "pages/budgets/ledger.html", {"ledger": ledger})


@login_required(login_url="/login/")
def budget_exceptions_view(request):
    exceptions = PurchaseRequisition.objects.filter(status=PurchaseRequisition.STATUS_BUDGET_REVIEW).order_by("-updated_at")
    return render(request, "pages/budgets/exceptions.html", {"exceptions": exceptions})

