from django.contrib import admin
from apps.receipts.models import GoodsReceipt, InspectionRecord, ReceiptLine, RejectionRecord
from apps.core.admin_site import RoleBasedModelAdmin, register_model


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0


class GoodsReceiptAdmin(RoleBasedModelAdmin):
    list_display = ("grn_number", "po", "received_by", "received_date", "delivery_note_number")
    search_fields = ("grn_number", "po__po_number", "delivery_note_number")
    inlines = [ReceiptLineInline]


register_model(GoodsReceipt, GoodsReceiptAdmin)
register_model(ReceiptLine)
register_model(InspectionRecord)
register_model(RejectionRecord)
