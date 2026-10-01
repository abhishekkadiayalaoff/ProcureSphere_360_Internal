from django.contrib import admin
from .models import SourcingEvent, BidInvite, VendorBid, BidLine, AwardDecision


class BidInviteInline(admin.TabularInline):
    model = BidInvite
    extra = 1


class BidLineInline(admin.TabularInline):
    model = BidLine
    extra = 1


@admin.register(SourcingEvent)
class SourcingEventAdmin(admin.ModelAdmin):
    list_display = ("event_number", "title", "event_type", "requisition", "status", "is_sealed", "bid_start_date", "bid_end_date")
    list_filter = ("event_type", "status", "is_sealed")
    search_fields = ("event_number", "title")
    inlines = [BidInviteInline]


@admin.register(VendorBid)
class VendorBidAdmin(admin.ModelAdmin):
    list_display = ("bid_number", "event", "vendor", "total_bid_amount", "status", "created_at")
    list_filter = ("status", "event")
    search_fields = ("bid_number", "vendor__legal_name")
    inlines = [BidLineInline]


@admin.register(AwardDecision)
class AwardDecisionAdmin(admin.ModelAdmin):
    list_display = ("event", "winning_bid", "approved_by", "created_at")
    search_fields = ("event__event_number", "award_reason")
