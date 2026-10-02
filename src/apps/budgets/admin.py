from django.contrib import admin
from .models import Budget, SpendLedger

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('cost_center', 'fiscal_period', 'allocated_amount', 'available_amount')
    list_filter = ('fiscal_period',)
    search_fields = ('cost_center__name',)

@admin.register(SpendLedger)
class SpendLedgerAdmin(admin.ModelAdmin):
    list_display = ('budget', 'entry_type', 'amount', 'reference_number', 'created_at')
    list_filter = ('entry_type',)
