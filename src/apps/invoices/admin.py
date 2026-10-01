from django.contrib import admin
from .models import SupplierInvoice, InvoiceLine, MatchException


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 1


class MatchExceptionInline(admin.StackedInline):
    model = MatchException
    extra = 0


@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "vendor", "po", "status", "total_amount", "invoice_date", "due_date")
    list_filter = ("status", "vendor")
    search_fields = ("invoice_number", "vendor__legal_name", "po__po_number")
    inlines = [InvoiceLineInline, MatchExceptionInline]


@admin.register(MatchException)
class MatchExceptionAdmin(admin.ModelAdmin):
    list_display = ("invoice", "exception_type", "status", "variance_amount", "resolved_by", "created_at")
    list_filter = ("exception_type", "status")
    search_fields = ("invoice__invoice_number", "description")
