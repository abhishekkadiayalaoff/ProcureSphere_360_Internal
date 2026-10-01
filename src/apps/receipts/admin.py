from django.contrib import admin
from .models import GoodsReceipt, ReceiptLine, InspectionRecord, RejectionRecord


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 1


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("grn_number", "po", "received_by", "received_date", "delivery_note_number")
    search_fields = ("grn_number", "po__po_number", "delivery_note_number")
    inlines = [ReceiptLineInline]


@admin.register(InspectionRecord)
class InspectionRecordAdmin(admin.ModelAdmin):
    list_display = ("receipt_line", "inspected_by", "passed", "created_at")
    list_filter = ("passed",)
    search_fields = ("inspection_notes", "inspected_by__email")


@admin.register(RejectionRecord)
class RejectionRecordAdmin(admin.ModelAdmin):
    list_display = ("receipt_line", "rejected_quantity", "returned_to_vendor", "created_at")
    list_filter = ("returned_to_vendor",)
    search_fields = ("rejection_reason",)
