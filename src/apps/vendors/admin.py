from django.contrib import admin
from .models import VendorCategory, Vendor, VendorContact, VendorDocument, VendorRiskRecord


class VendorContactInline(admin.TabularInline):
    model = VendorContact
    extra = 1


class VendorDocumentInline(admin.TabularInline):
    model = VendorDocument
    extra = 1


@admin.register(VendorCategory)
class VendorCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "vendor_number", "tax_identification_number", "category", "status", "email", "phone")
    list_filter = ("status", "category")
    search_fields = ("legal_name", "vendor_number", "tax_identification_number", "email")
    inlines = [VendorContactInline, VendorDocumentInline]


@admin.register(VendorRiskRecord)
class VendorRiskRecordAdmin(admin.ModelAdmin):
    list_display = ("vendor", "risk_level", "assessed_by", "created_at")
    list_filter = ("risk_level",)
    search_fields = ("vendor__legal_name", "assessment_notes")
