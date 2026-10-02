from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.budgets.models import Budget, SpendLedger

@login_required(login_url="/login/")
def list_view(request):
    budgets = Budget.objects.select_related('cost_center', 'fiscal_period').all()
    return render(
        request,
        "pages/budgets/list.html",
        {"budgets": budgets}
    )

@login_required(login_url="/login/")
def ledger_view(request):
    ledger = SpendLedger.objects.select_related('budget__cost_center').order_by("-created_at")
    return render(
        request,
        "pages/budgets/ledger.html",
        {"ledger": ledger}
    )
