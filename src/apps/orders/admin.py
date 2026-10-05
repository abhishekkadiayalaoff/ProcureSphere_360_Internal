from django.contrib import admin
from .models import PurchaseOrder, POLine, POAmendment, DeliverySchedule


class POLineInline(admin.TabularInline):
    model = POLine
    extra = 0


class POAmendmentInline(admin.TabularInline):
    model = POAmendment
    extra = 0
    readonly_fields = ("amendment_number", "reason", "created_at")


class DeliveryScheduleInline(admin.TabularInline):
    model = DeliverySchedule
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "vendor", "version", "status", "total_amount", "created_at", "acknowledged_at")
    list_filter = ("status", "version")
    search_fields = ("po_number", "vendor__legal_name")
    inlines = [POLineInline, DeliveryScheduleInline, POAmendmentInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(DeliverySchedule)
class DeliveryScheduleAdmin(admin.ModelAdmin):
    list_display = ("po", "po_line", "expected_delivery_date", "quantity_expected", "status")
    list_filter = ("status",)
    search_fields = ("po__po_number", "po_line__item_description")
