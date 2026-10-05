from django.contrib import admin
from apps.scorecards.models import VendorScorecard
from apps.core.admin_site import RoleBasedModelAdmin, register_model


class VendorScorecardAdmin(RoleBasedModelAdmin):
    list_display = ("vendor", "evaluation_period", "composite_score", "delivery_score", "quality_score", "price_score", "compliance_score")
    list_filter = ("evaluation_period",)
    search_fields = ("vendor__legal_name",)


register_model(VendorScorecard, VendorScorecardAdmin)
