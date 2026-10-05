from django.contrib import admin
from apps.requisitions.models import PRAttachment, PRLine, PurchaseRequisition
from apps.core.admin_site import RoleBasedModelAdmin, register_model


class PRLineInline(admin.TabularInline):
    model = PRLine
    extra = 0


class PurchaseRequisitionAdmin(RoleBasedModelAdmin):
    list_display = ("pr_number", "title", "requester", "department", "total_amount", "status", "created_at")
    list_filter = ("status", "department")
    search_fields = ("pr_number", "title", "requester__email")
    inlines = [PRLineInline]


register_model(PurchaseRequisition, PurchaseRequisitionAdmin)
register_model(PRLine)
register_model(PRAttachment)
