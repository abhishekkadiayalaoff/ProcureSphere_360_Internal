from django.contrib import admin
from .models import PurchaseRequisition, PRLine, PRAttachment


class PRLineInline(admin.TabularInline):
    model = PRLine
    extra = 1


class PRAttachmentInline(admin.TabularInline):
    model = PRAttachment
    extra = 1


@admin.register(PurchaseRequisition)
class PurchaseRequisitionAdmin(admin.ModelAdmin):
    list_display = ("pr_number", "title", "requester", "department", "cost_center", "status", "total_amount", "created_at")
    list_filter = ("status", "department", "cost_center")
    search_fields = ("pr_number", "title", "requester__email")
    inlines = [PRLineInline, PRAttachmentInline]
