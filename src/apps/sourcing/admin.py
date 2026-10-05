from django.contrib import admin
from .models import SourcingEvent, BidInvite, VendorBid, BidLine, BidVersion, BidAttachment, Clarification, BidEvaluation


class BidInviteInline(admin.TabularInline):
    model = BidInvite
    extra = 0


@admin.register(SourcingEvent)
class SourcingEventAdmin(admin.ModelAdmin):
    list_display = ("event_number", "title", "event_type", "status", "bid_start_date", "bid_end_date", "is_sealed")
    list_filter = ("event_type", "status", "is_sealed")
    search_fields = ("event_number", "title", "description")
    inlines = [BidInviteInline]


class BidLineInline(admin.TabularInline):
    model = BidLine
    extra = 0


class BidVersionInline(admin.TabularInline):
    model = BidVersion
    extra = 0
    readonly_fields = ("version_number", "total_bid_amount", "amendment_reason", "created_at")


class BidAttachmentInline(admin.TabularInline):
    model = BidAttachment
    extra = 0


@admin.register(VendorBid)
class VendorBidAdmin(admin.ModelAdmin):
    list_display = ("bid_number", "event", "vendor", "version", "status", "total_bid_amount", "submitted_at")
    list_filter = ("status", "version")
    search_fields = ("bid_number", "event__event_number", "vendor__legal_name")
    inlines = [BidLineInline, BidVersionInline, BidAttachmentInline]


@admin.register(Clarification)
class ClarificationAdmin(admin.ModelAdmin):
    list_display = ("event", "vendor", "status", "created_at", "answered_at")
    list_filter = ("status",)
    search_fields = ("question", "answer", "event__event_number", "vendor__legal_name")


@admin.register(BidEvaluation)
class BidEvaluationAdmin(admin.ModelAdmin):
    list_display = ("event", "bid", "evaluator", "weighted_total_score", "created_at")
    search_fields = ("event__event_number", "bid__bid_number")
