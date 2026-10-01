from django.contrib import admin
from .models import VendorScorecard


@admin.register(VendorScorecard)
class VendorScorecardAdmin(admin.ModelAdmin):
    list_display = ("vendor", "evaluation_period", "composite_score", "delivery_score", "quality_score", "price_score", "compliance_score", "evaluated_by")
    list_filter = ("evaluation_period", "vendor")
    search_fields = ("vendor__legal_name", "evaluator_comments")
