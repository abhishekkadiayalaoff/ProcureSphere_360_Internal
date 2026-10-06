from datetime import timedelta

from django.utils import timezone

from .models import Vendor, VendorDocument


def get_all_vendors():
    return Vendor.objects.select_related("category").order_by("-created_at")


def get_all_active_vendors():
    return (
        Vendor.objects.select_related("category")
        .filter(status=Vendor.STATUS_ACTIVE)
        .order_by("legal_name")
    )


def get_vendor_by_id(vendor_id):
    return (
        Vendor.objects.select_related("category")
        .prefetch_related("documents", "contacts", "risk_records")
        .filter(id=vendor_id)
        .first()
    )


def get_vendors_by_status(status_code):
    return (
        Vendor.objects.select_related("category").filter(status=status_code).order_by("-created_at")
    )


def get_vendor_documents(vendor_id):
    return (
        VendorDocument.objects.select_related("verified_by")
        .filter(vendor_id=vendor_id)
        .order_by("-created_at")
    )


def get_vendor_dashboard_metrics(vendor, user=None):
    """
    Computes real backend metrics for the Vendor Dashboard.
    Zero hardcoded values.
    """
    from apps.notifications.models import Notification
    from apps.orders.models import PurchaseOrder
    from apps.sourcing.models import BidInvite, Clarification, SourcingEvent, VendorBid

    if not vendor:
        return {
            "active_rfq_invitations": 0,
            "bids_in_draft": 0,
            "submitted_bids": 0,
            "upcoming_deadlines": 0,
            "pending_clarifications": 0,
            "pos_requiring_ack": 0,
            "active_pos": 0,
            "kyc_compliance_status": "DRAFT",
            "unread_notifications": 0,
        }

    now = timezone.now()

    # Active RFQ/RFP Invitations: Invited and currently in BID_WINDOW
    active_invitations_count = BidInvite.objects.filter(
        vendor=vendor,
        event__status=SourcingEvent.STATUS_BID_WINDOW,
    ).count()

    # Bids in Draft
    bids_in_draft_count = VendorBid.objects.filter(
        vendor=vendor,
        status=VendorBid.STATUS_DRAFT,
    ).count()

    # Submitted Bids (Submitted or Amended)
    submitted_bids_count = VendorBid.objects.filter(
        vendor=vendor,
        status__in=[VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED],
    ).count()

    # Upcoming Deadlines: Open events closing in next 7 days
    upcoming_deadlines_count = BidInvite.objects.filter(
        vendor=vendor,
        event__status=SourcingEvent.STATUS_BID_WINDOW,
        event__bid_end_date__gte=now,
        event__bid_end_date__lte=now + timedelta(days=7),
    ).count()

    # Pending Clarifications
    pending_clarifications_count = Clarification.objects.filter(
        vendor=vendor,
        status="PENDING",
    ).count()

    # POs Requiring Acknowledgement (ISSUED status)
    pos_requiring_ack_count = PurchaseOrder.objects.filter(
        vendor=vendor,
        status=PurchaseOrder.STATUS_ISSUED,
    ).count()

    # Active POs (ISSUED, ACKNOWLEDGED, PARTIAL_RECEIPT)
    active_pos_count = PurchaseOrder.objects.filter(
        vendor=vendor,
        status__in=[
            PurchaseOrder.STATUS_ISSUED,
            PurchaseOrder.STATUS_ACKNOWLEDGED,
            PurchaseOrder.STATUS_PARTIAL_RECEIPT,
        ],
    ).count()

    # Notifications
    unread_notifications = 0
    if user and user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            recipient=user,
            is_read=False,
        ).count()

    return {
        "active_rfq_invitations": active_invitations_count,
        "bids_in_draft": bids_in_draft_count,
        "submitted_bids": submitted_bids_count,
        "upcoming_deadlines": upcoming_deadlines_count,
        "pending_clarifications": pending_clarifications_count,
        "pos_requiring_ack": pos_requiring_ack_count,
        "active_pos": active_pos_count,
        "kyc_compliance_status": vendor.status,
        "unread_notifications": unread_notifications,
    }


# ==============================================================================
# VENDOR GOVERNANCE (internal procurement view)
# ==============================================================================


def get_governance_vendor_queryset():
    from .filters import annotate_governance

    return annotate_governance(Vendor.objects.select_related("category")).order_by("-updated_at")


def get_governance_metrics() -> dict:
    """Database-backed governance KPIs (single aggregate query + two subquery counts)."""
    from django.db.models import Count, Q

    from .filters import PERFORMANCE_ISSUE_THRESHOLD, annotate_governance
    from .models import VendorRiskRecord

    counts = Vendor.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Vendor.STATUS_ACTIVE)),
        pending_review=Count(
            "id",
            filter=Q(
                status__in=[
                    Vendor.STATUS_SUBMITTED,
                    Vendor.STATUS_KYC_REVIEW,
                    Vendor.STATUS_APPROVED,
                ]
            ),
        ),
        on_hold=Count("id", filter=Q(status=Vendor.STATUS_ON_HOLD)),
        suspended=Count("id", filter=Q(status=Vendor.STATUS_SUSPENDED)),
    )
    annotated = annotate_governance(Vendor.objects.all())
    high_risk = annotated.filter(latest_risk_level=VendorRiskRecord.RISK_LEVEL_HIGH)
    perf_issues = annotated.filter(latest_composite_score__lt=PERFORMANCE_ISSUE_THRESHOLD)
    today = timezone.now().date()
    expired_docs = Vendor.objects.filter(
        status=Vendor.STATUS_ACTIVE, documents__expiry_date__lt=today
    )
    attention_ids = (
        set(high_risk.values_list("id", flat=True))
        | set(perf_issues.values_list("id", flat=True))
        | set(expired_docs.values_list("id", flat=True))
        | set(Vendor.objects.filter(status=Vendor.STATUS_ON_HOLD).values_list("id", flat=True))
    )
    counts.update(
        {
            "high_risk": high_risk.count(),
            "performance_issues": perf_issues.count(),
            "requiring_attention": len(attention_ids),
        }
    )
    return counts


def get_vendor_open_transactions(vendor) -> dict:
    """
    Open sourcing / bid / PO exposure for a vendor; shown before hold/suspension
    (PRD 4.2 edge case: suspension while open sourcing or PO transactions exist).
    """
    from apps.orders.models import PurchaseOrder
    from apps.sourcing.models import BidInvite, SourcingEvent, VendorBid

    open_event_statuses = [
        SourcingEvent.STATUS_DRAFT,
        SourcingEvent.STATUS_PUBLISHED,
        SourcingEvent.STATUS_BID_WINDOW,
        SourcingEvent.STATUS_TECHNICAL_REVIEW,
        SourcingEvent.STATUS_COMMERCIAL_REVIEW,
        SourcingEvent.STATUS_AWARD_APPROVAL,
    ]
    invites = BidInvite.objects.filter(
        vendor=vendor, event__status__in=open_event_statuses
    ).select_related("event")
    bids = VendorBid.objects.filter(
        vendor=vendor,
        event__status__in=open_event_statuses,
        status__in=[VendorBid.STATUS_DRAFT, VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED],
    ).select_related("event")
    pending_awards = SourcingEvent.objects.filter(
        status=SourcingEvent.STATUS_AWARD_APPROVAL,
        award_decisions__status="PENDING",
        award_decisions__winning_bid__vendor=vendor,
    )
    open_pos = PurchaseOrder.objects.filter(
        vendor=vendor,
        status__in=[
            PurchaseOrder.STATUS_DRAFT,
            PurchaseOrder.STATUS_APPROVAL,
            PurchaseOrder.STATUS_ISSUED,
            PurchaseOrder.STATUS_ACKNOWLEDGED,
            PurchaseOrder.STATUS_PARTIAL_RECEIPT,
        ],
    )
    return {
        "open_invitations": list(invites),
        "open_bids": list(bids),
        "pending_awards": list(pending_awards),
        "open_pos": list(open_pos),
        "summary": {
            "open_invitations": invites.count(),
            "open_bids": bids.count(),
            "pending_awards": pending_awards.count(),
            "open_pos": open_pos.count(),
        },
    }


def get_vendor_change_history(vendor, limit=100):
    """AuditLog entries for the vendor and its documents / risk records / scorecards."""
    from django.db.models import Q

    from apps.audit.models import AuditLog

    doc_ids = [str(i) for i in vendor.documents.values_list("id", flat=True)]
    risk_ids = [str(i) for i in vendor.risk_records.values_list("id", flat=True)]
    score_ids = [str(i) for i in vendor.scorecards.values_list("id", flat=True)]
    return (
        AuditLog.objects.filter(
            Q(target_model="Vendor", target_object_id=str(vendor.id))
            | Q(target_model="VendorDocument", target_object_id__in=doc_ids)
            | Q(target_model="VendorRiskRecord", target_object_id__in=risk_ids)
            | Q(target_model="VendorScorecard", target_object_id__in=score_ids)
        )
        .select_related("actor", "actor__role")
        .order_by("-timestamp")[:limit]
    )


def get_vendor_sourcing_history(vendor, limit=20):
    from apps.sourcing.models import BidInvite

    return (
        BidInvite.objects.filter(vendor=vendor)
        .select_related("event")
        .order_by("-created_at")[:limit]
    )


def get_vendor_purchase_orders(vendor, limit=20):
    from apps.orders.models import PurchaseOrder

    return PurchaseOrder.objects.filter(vendor=vendor).order_by("-created_at")[:limit]
