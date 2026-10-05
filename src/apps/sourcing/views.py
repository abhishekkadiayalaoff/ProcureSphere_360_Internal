from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from .models import SourcingEvent, VendorBid
from .selectors import get_all_sourcing_events, get_sealed_vendor_bids
from .services import evaluate_and_award_sourcing_event_service


@login_required
def sourcing_list_view(request):
    """
    Sourcing Events (RFQ / RFP) dashboard view.
    """
    status_filter = request.GET.get("status", "")
    events = get_all_sourcing_events()

    if status_filter:
        events = events.filter(status=status_filter)

    return render(
        request,
        "sourcing/sourcing_list.html",
        {
            "events": events,
            "status_filter": status_filter,
        },
    )


@login_required
def sourcing_detail_view(request, event_id):
    """
    Detailed Sourcing Event view enforcing stage-gated sealed bid secrecy.
    """
    event = get_object_or_404(SourcingEvent, id=event_id)
    bids = get_sealed_vendor_bids(event, request.user)

    if request.method == "POST" and "award_winning_bid" in request.POST:
        winning_bid_id = request.POST.get("winning_bid_id")
        comments = request.POST.get("comments", "").strip()

        try:
            winning_bid = VendorBid.objects.get(id=winning_bid_id, event=event)
            evaluate_and_award_sourcing_event_service(
                event=event,
                winning_bid=winning_bid,
                award_reason=comments,
                approved_by_user=request.user,
            )
            messages.success(request, f"Sourcing Event {event.event_number} awarded to {winning_bid.vendor.legal_name}!")
            return redirect(f"/sourcing-events/{event.id}/")
        except Exception as e:
            messages.error(request, f"Error awarding sourcing event: {str(e)}")

    return render(
        request,
        "sourcing/sourcing_detail.html",
        {
            "event": event,
            "bids": bids,
            "is_sealed": event.status == "BID_WINDOW" and not request.user.is_superuser,
        },
    )


@login_required

def sourcing_create_view(request):
    """
    HTMX modal / page view to create a new Sourcing Event (RFQ/RFP).
    """
    from datetime import datetime
    from django.utils import timezone
    from apps.requisitions.models import PurchaseRequisition
    from .services import create_sourcing_event_service

    requisitions = PurchaseRequisition.objects.filter(status="APPROVED")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        event_type = request.POST.get("event_type", "RFQ")
        bid_start_str = request.POST.get("bid_start_date")
        bid_end_str = request.POST.get("bid_end_date")
        req_id = request.POST.get("requisition_id")
        description = request.POST.get("description", "").strip()

        try:
            bid_start_date = datetime.strptime(bid_start_str, "%Y-%m-%d").date() if bid_start_str else timezone.now().date()
            bid_end_date = datetime.strptime(bid_end_str, "%Y-%m-%d").date() if bid_end_str else timezone.now().date() + timezone.timedelta(days=14)
        except ValueError:
            bid_start_date = timezone.now().date()
            bid_end_date = timezone.now().date() + timezone.timedelta(days=14)

        requisition = PurchaseRequisition.objects.filter(id=req_id).first() if req_id else None

        try:
            event = create_sourcing_event_service(
                title=title,
                event_type=event_type,
                bid_start_date=bid_start_date,
                bid_end_date=bid_end_date,
                description=description,
                requisition=requisition,
                created_by_user=request.user,
            )
            messages.success(request, f"Sourcing Event {event.event_number} created successfully as DRAFT.")
            return redirect(f"/sourcing-events/{event.id}/")
        except Exception as e:
            messages.error(request, f"Error creating sourcing event: {str(e)}")

    return render(
        request,
        "sourcing/partials/sourcing_create_modal.html",
        {"requisitions": requisitions},
    )


