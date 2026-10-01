from django.contrib import admin
from .models import PurchaseOrder, POLine, POAmendment


class POLineInline(admin.TabularInline):
    model = POLine
    extra = 1


class POAmendmentInline(admin.StackedInline):
    model = POAmendment
    extra = 0
    readonly_fields = ("previous_version_snapshot",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "version", "vendor", "requisition", "cost_center", "status", "total_amount", "created_at")
    list_filter = ("status", "cost_center")
    search_fields = ("po_number", "vendor__legal_name")
    inlines = [POLineInline, POAmendmentInline]
