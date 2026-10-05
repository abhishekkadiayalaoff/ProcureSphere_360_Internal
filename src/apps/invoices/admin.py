from django.contrib import admin
from apps.invoices.models import InvoiceLine, MatchException, SupplierInvoice
from apps.core.admin_site import RoleBasedModelAdmin, register_model


class SupplierInvoiceAdmin(RoleBasedModelAdmin):
    list_display = ("invoice_number", "vendor", "po", "total_amount", "status", "invoice_date", "created_at")
    list_filter = ("status",)
    search_fields = ("invoice_number", "vendor__legal_name", "po__po_number")


class MatchExceptionAdmin(RoleBasedModelAdmin):
    list_display = ("invoice", "exception_type", "variance_amount", "status", "created_at")
    list_filter = ("status", "exception_type")
    search_fields = ("invoice__invoice_number", "description")


register_model(SupplierInvoice, SupplierInvoiceAdmin)
register_model(InvoiceLine)
register_model(MatchException, MatchExceptionAdmin)
