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
