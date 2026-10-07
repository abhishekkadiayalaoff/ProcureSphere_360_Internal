from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.audit.models import AuditLog
from apps.vendors.models import VendorCategory

from . import services
from .dashboard_selectors import (
    build_commercial_comparison,
    get_bid_portal_events,
    get_bid_portal_metrics,
    get_bid_portal_rows,
    get_decision_audit,
    get_evaluation_events,
    get_evaluation_metrics,
)
from .forms import SourcingEventForm
from .models import BidInvite, Clarification, SourcingEvent, VendorBid
from .permissions import (
    can_approve_award,
    can_manage_events,
    can_read_bids,
    can_view_events,
    sourcing_capabilities,
)
from .selectors import (
    build_evaluation_rows,
    get_all_sourcing_events,
    get_bid_attachments_for_evaluator,
    get_eligible_vendors_for_event,
    get_invitation_rows,
    get_sourcing_dashboard_metrics,
    search_sourcing_events,
)

PAGE_SIZE = 20

LIFECYCLE = [
    SourcingEvent.STATUS_DRAFT,
    SourcingEvent.STATUS_PUBLISHED,
    SourcingEvent.STATUS_BID_WINDOW,
    SourcingEvent.STATUS_TECHNICAL_REVIEW,
    SourcingEvent.STATUS_COMMERCIAL_REVIEW,
    SourcingEvent.STATUS_AWARD_APPROVAL,
    SourcingEvent.STATUS_AWARDED,
]

STATUS_FILTERS = [
    ("", "All"),
    ("OPEN", "Active"),
    ("DRAFT", "Draft"),
    ("PUBLISHED", "Published"),
    ("BID_WINDOW", "Bid window"),
    ("CLOSING_SOON", "Closing soon"),
    ("EVALUATION", "Evaluation"),
    ("COMMERCIAL_REVIEW", "Negotiation / commercial"),
    ("AWARD_APPROVAL", "Award approval"),
    ("AWARDED", "Awarded"),
    ("CANCELLED", "Cancelled"),
]


def _require_view(user):
    if not can_view_events(user):
        raise PermissionDenied("RFQ/RFP sourcing is restricted to internal procurement roles.")


def _require_manage(user):
    if not can_manage_events(user):
        raise PermissionDenied("Your role cannot modify sourcing events.")


@login_required(login_url="/login/")
def sourcing_list_view(request):
    """RFQ/RFP register: KPIs, server-side search/filter and pagination."""
    _require_view(request.user)
    services.sync_all_event_windows()

    params = request.GET.copy()
    if params.get("status") == "EVALUATION":
        events = get_all_sourcing_events().filter(
            status__in=[
                SourcingEvent.STATUS_TECHNICAL_REVIEW,
                SourcingEvent.STATUS_COMMERCIAL_REVIEW,
            ]
        )
        params.pop("status")
        events = search_sourcing_events(events, params)
    else:
        events = search_sourcing_events(get_all_sourcing_events(), params)

    page = Paginator(events, PAGE_SIZE).get_page(request.GET.get("page"))
    qs = request.GET.copy()
    qs.pop("page", None)
    return render(
        request,
        "sourcing/sourcing_list.html",
        {
            "page_obj": page,
            "events": page.object_list,
            "metrics": get_sourcing_dashboard_metrics(),
            "status_filters": STATUS_FILTERS,
            "status_filter": request.GET.get("status", ""),
            "type_choices": SourcingEvent.EVENT_TYPE_CHOICES,
            "categories": VendorCategory.objects.order_by("name"),
            "params": request.GET,
            "querystring": qs.urlencode(),
            "caps": sourcing_capabilities(request.user),
        },
    )


def _form_to_kwargs(cleaned):
    return {
        "title": cleaned["title"],
        "event_type": cleaned["event_type"],
        "bid_start_date": cleaned["bid_start_date"],
        "bid_end_date": cleaned["bid_end_date"],
        "description": cleaned["description"],
        "technical_requirements": cleaned["technical_requirements"],
        "commercial_requirements": cleaned["commercial_requirements"],
        "required_documents": cleaned["required_documents"],
        "requisition": cleaned["requisition"],
        "technical_weight": cleaned["technical_weight"],
        "commercial_weight": cleaned["commercial_weight"],
    }


@login_required(login_url="/login/")
def sourcing_create_view(request):
    _require_manage(request.user)
    form = SourcingEventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            event = services.create_sourcing_event_service(
                **_form_to_kwargs(form.cleaned_data), created_by_user=request.user
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(
                request,
                f"{event.event_number} created as DRAFT. Invite eligible vendors, then publish.",
            )
            return redirect("sourcing_detail", event_id=event.id)
    return render(request, "sourcing/sourcing_form.html", {"form": form, "event": None})


@login_required(login_url="/login/")
def sourcing_edit_view(request, event_id):
    _require_manage(request.user)
    event = get_object_or_404(SourcingEvent, pk=event_id)
    if event.status != SourcingEvent.STATUS_DRAFT:
        messages.error(request, "Only DRAFT events can be edited.")
        return redirect("sourcing_detail", event_id=event.id)
    form = SourcingEventForm(
        request.POST or None, initial=SourcingEventForm.initial_from_event(event)
    )
    if request.method == "POST" and form.is_valid():
        try:
            services.update_draft_sourcing_event_service(
                event=event, user=request.user, data=_form_to_kwargs(form.cleaned_data)
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"{event.event_number} updated.")
            return redirect("sourcing_detail", event_id=event.id)
    return render(request, "sourcing/sourcing_form.html", {"form": form, "event": event})


def _lifecycle_steps(event):
    if event.status == SourcingEvent.STATUS_CANCELLED:
        return [
            {"code": s, "label": dict(SourcingEvent.STATUS_CHOICES)[s], "state": "todo"}
            for s in LIFECYCLE
        ]
    current = LIFECYCLE.index(event.status)
    return [
        {
            "code": s,
            "label": dict(SourcingEvent.STATUS_CHOICES)[s],
            "state": "done" if i < current else ("current" if i == current else "todo"),
        }
        for i, s in enumerate(LIFECYCLE)
    ]


def _event_audit_trail(event):
    related_ids = [str(event.id)]
    related_ids += [str(i) for i in event.invitations.values_list("id", flat=True)]
    related_ids += [str(i) for i in event.award_decisions.values_list("id", flat=True)]
    related_ids += [str(i) for i in event.evaluations.values_list("id", flat=True)]
    related_ids += [str(i) for i in event.negotiation_notes.values_list("id", flat=True)]
    related_ids += [str(i) for i in event.clarifications.values_list("id", flat=True)]
    return (
        AuditLog.objects.filter(
            target_model__in=[
                "SourcingEvent",
                "BidInvite",
                "AwardDecision",
                "BidEvaluation",
                "NegotiationNote",
                "Clarification",
            ],
            target_object_id__in=related_ids,
        )
        .select_related("actor", "actor__role")
        .order_by("-timestamp")[:100]
    )


@login_required(login_url="/login/")
def sourcing_detail_view(request, event_id):
    """Event workspace: lifecycle, invitations, clarifications, evaluation, award and PO."""
    _require_view(request.user)
    event = get_object_or_404(SourcingEvent.objects.select_related("requisition"), pk=event_id)
    services.sync_event_window_status(event=event)
    caps = sourcing_capabilities(request.user)

    can_invite = caps["can_manage"] and event.status in (
        SourcingEvent.STATUS_DRAFT,
        SourcingEvent.STATUS_PUBLISHED,
        SourcingEvent.STATUS_BID_WINDOW,
    )
    eligible_vendors = []
    if can_invite:
        eligible_vendors = get_eligible_vendors_for_event(
            event, category_id=request.GET.get("inv_cat") or None, q=request.GET.get("inv_q", "")
        )[:100]

    from apps.orders.models import PurchaseOrder

    context = {
        "event": event,
        "caps": caps,
        "steps": _lifecycle_steps(event),
        "publish_errors": (
            services.get_publish_validation_errors(event)
            if event.status == SourcingEvent.STATUS_DRAFT
            else []
        ),
        "invitation_rows": get_invitation_rows(event),
        "can_invite": can_invite,
        "eligible_vendors": eligible_vendors,
        "categories": VendorCategory.objects.order_by("name"),
        "inv_q": request.GET.get("inv_q", ""),
        "inv_cat": request.GET.get("inv_cat", ""),
        "submitted_count": event.bids.filter(
            status__in=[VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED]
        ).count(),
        "clarifications": event.clarifications.select_related("vendor", "answered_by").order_by(
            "-created_at"
        ),
        "current_decision": event.award_decision,
        "purchase_orders": PurchaseOrder.objects.filter(sourcing_event=event).order_by(
            "-created_at"
        ),
        "audit_trail": _event_audit_trail(event),
        "is_deadline_passed": event.bid_end_date < timezone.now(),
    }
    return render(request, "sourcing/sourcing_detail.html", context)


# ------------------------------------------------------------------------------------------
# POST action dispatcher (every action: auth -> role -> object -> service (validates,
# persists, audits, notifies) -> redirect with result)
# ------------------------------------------------------------------------------------------


def _bid(event, request):
    return get_object_or_404(VendorBid, pk=request.POST.get("bid_id"), event=event)


def _act_publish(event, request):
    services.publish_sourcing_event_service(event=event, user=request.user)
    event.refresh_from_db()
    return (
        f"{event.event_number} published ({event.get_status_display()}). Invited vendors notified."
    )


def _act_close(event, request):
    services.close_bid_window_service(event=event, user=request.user)
    return "Bid window closed. Technical review started."


def _act_commercial(event, request):
    services.advance_to_commercial_review_service(event=event, user=request.user)
    return "Technical review complete. Commercial envelopes unsealed."


def _act_cancel(event, request):
    services.cancel_sourcing_event_service(
        event=event, user=request.user, reason=request.POST.get("reason", "")
    )
    return f"{event.event_number} cancelled."


def _act_invite(event, request):
    vendor_ids = request.POST.getlist("vendor_ids")
    invites = services.invite_vendors_to_event_service(
        event=event, vendor_ids=vendor_ids, invited_by=request.user
    )
    return f"{len(invites)} vendor(s) invited."


def _act_revoke(event, request):
    invite = get_object_or_404(BidInvite, pk=request.POST.get("invite_id"), event=event)
    services.revoke_invitation_service(invite=invite, user=request.user)
    return "Invitation removed."


def _act_answer(event, request):
    clarification = get_object_or_404(
        Clarification, pk=request.POST.get("clarification_id"), event=event
    )
    services.answer_clarification_service(
        clarification=clarification, user=request.user, answer=request.POST.get("answer", "")
    )
    return "Clarification answered and vendor notified."


def _act_tech_score(event, request):
    services.record_technical_evaluation_service(
        event=event,
        bid=_bid(event, request),
        evaluator=request.user,
        score=request.POST.get("score"),
        comments=request.POST.get("comments", ""),
    )
    return "Technical score saved."


def _act_comm_score(event, request):
    services.record_commercial_evaluation_service(
        event=event,
        bid=_bid(event, request),
        evaluator=request.user,
        score=request.POST.get("score"),
        comments=request.POST.get("comments", ""),
    )
    return "Commercial score saved."


def _act_negotiate(event, request):
    services.add_negotiation_note_service(
        event=event,
        bid=_bid(event, request),
        author=request.user,
        note=request.POST.get("note", ""),
    )
    return "Negotiation note recorded."


def _act_recommend(event, request):
    services.recommend_award_service(
        event=event,
        winning_bid=_bid(event, request),
        recommended_by=request.user,
        award_reason=request.POST.get("award_reason", ""),
    )
    return "Award recommendation submitted for Procurement Manager approval."


def _act_approve(event, request):
    services.approve_award_service(
        event=event, approver=request.user, comments=request.POST.get("comments", "")
    )
    return "Award approved. The event is AWARDED."


def _act_reject(event, request):
    services.reject_award_service(
        event=event, approver=request.user, comments=request.POST.get("reason", "")
    )
    return "Award recommendation rejected; event returned to commercial review."


def _act_generate_po(event, request):
    from apps.organization.models import CostCenter

    cc_id = request.POST.get("cost_center_id")
    cost_center = get_object_or_404(CostCenter, pk=cc_id) if cc_id else None
    po = services.generate_po_from_award_service(
        event=event, user=request.user, cost_center=cost_center
    )
    return f"Purchase Order {po.po_number} generated from the award."


ACTIONS = {
    "publish": (_act_publish, "manage"),
    "close": (_act_close, "manage"),
    "start-commercial": (_act_commercial, "manage"),
    "cancel": (_act_cancel, "manage"),
    "invite": (_act_invite, "manage"),
    "revoke-invite": (_act_revoke, "manage"),
    "answer-clarification": (_act_answer, "manage"),
    "technical-score": (_act_tech_score, "manage"),
    "commercial-score": (_act_comm_score, "manage"),
    "negotiation-note": (_act_negotiate, "manage"),
    "recommend-award": (_act_recommend, "manage"),
    "approve-award": (_act_approve, "approve"),
    "reject-award": (_act_reject, "approve"),
    "generate-po": (_act_generate_po, "manage"),
}

ACTION_REDIRECTS = {
    "invite": ("sourcing_detail", "invitations"),
    "revoke-invite": ("sourcing_detail", "invitations"),
    "answer-clarification": ("sourcing_detail", "clarifications"),
    "close": ("bid_portal_event", ""),
    "technical-score": ("evaluation_event", "technical"),
    "start-commercial": ("evaluation_event", "commercial"),
    "commercial-score": ("evaluation_event", "commercial"),
    "negotiation-note": ("evaluation_event", "negotiation"),
    "recommend-award": ("evaluation_event", "award"),
    "approve-award": ("evaluation_event", "award"),
    "reject-award": ("evaluation_event", "award"),
    "generate-po": ("evaluation_event", "award"),
}


@login_required(login_url="/login/")
@require_POST
def sourcing_action_view(request, event_id, action):
    handler, capability = ACTIONS.get(action, (None, None))
    if handler is None:
        raise Http404("Unknown sourcing action.")
    allowed = (
        can_approve_award(request.user)
        if capability == "approve"
        else can_manage_events(request.user)
    )
    if not allowed:
        raise PermissionDenied("Your role is not authorised for this sourcing action.")
    event = get_object_or_404(SourcingEvent, pk=event_id)
    try:
        messages.success(request, handler(event, request))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    url_name, anchor = ACTION_REDIRECTS.get(action, ("sourcing_detail", ""))
    response = redirect(url_name, event_id=event.id)
    if anchor:
        response["Location"] += f"#{anchor}"
    return response


@login_required(login_url="/login/")
def sourcing_attachment_download_view(request, event_id, attachment_id):
    """Stage-gated bid attachment download for evaluators (commercial after unsealing)."""
    _require_view(request.user)
    event = get_object_or_404(SourcingEvent, pk=event_id)
    allowed = get_bid_attachments_for_evaluator(event, request.user)
    attachment = get_object_or_404(allowed, pk=attachment_id)
    try:
        return FileResponse(attachment.file.open("rb"), as_attachment=True)
    except (FileNotFoundError, ValueError):
        raise Http404("Attachment file is not available in storage.")


# ------------------------------------------------------------------------------------------
# Vendor Bid Portal monitor & Evaluation and Award workspaces
# ------------------------------------------------------------------------------------------


def _require_bid_access(user):
    if not can_read_bids(user):
        raise PermissionDenied("Bid monitoring and evaluation are restricted to procurement roles.")


@login_required(login_url="/login/")
def bid_portal_dashboard_view(request):
    """Vendor Bid Portal dashboard: live bid windows and response tracking (sealed)."""
    _require_bid_access(request.user)
    services.sync_all_event_windows()
    return render(
        request,
        "sourcing/bid_portal_dashboard.html",
        {
            "metrics": get_bid_portal_metrics(),
            "events": get_bid_portal_events(),
            "caps": sourcing_capabilities(request.user),
        },
    )


@login_required(login_url="/login/")
def bid_portal_event_view(request, event_id):
    """Per-event bid portal monitor: access, validation, attachments, amendments, sealing."""
    _require_bid_access(request.user)
    event = get_object_or_404(SourcingEvent, pk=event_id)
    services.sync_event_window_status(event=event)
    rows = get_bid_portal_rows(event)
    responses = (VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED)
    return render(
        request,
        "sourcing/bid_portal_event.html",
        {
            "event": event,
            "rows": rows,
            "sealed": not event.bids_visible_to_evaluators,
            "is_deadline_passed": event.bid_end_date < timezone.now(),
            "caps": sourcing_capabilities(request.user),
            "summary": {
                "invited": len(rows),
                "responded": sum(1 for r in rows if r["invite"].is_responded),
                "submitted": sum(1 for r in rows if r["bid"] and r["bid"].status in responses),
                "invalid": sum(
                    1 for r in rows if r["validation"] and not r["validation"]["is_valid"]
                ),
            },
        },
    )


@login_required(login_url="/login/")
def evaluation_dashboard_view(request):
    """Evaluation & Award dashboard: technical/commercial review, award approval, awarded."""
    _require_bid_access(request.user)
    services.sync_all_event_windows()
    status = request.GET.get("status", "")
    return render(
        request,
        "sourcing/evaluation_dashboard.html",
        {
            "metrics": get_evaluation_metrics(),
            "events": get_evaluation_events(status),
            "status": status,
            "caps": sourcing_capabilities(request.user),
        },
    )


@login_required(login_url="/login/")
def evaluation_event_view(request, event_id):
    """
    Evaluation & Award workspace: weighted technical scoring, commercial comparison,
    negotiation notes, award recommendation/approval, PO generation and decision audit.
    """
    from apps.orders.models import PurchaseOrder
    from apps.organization.models import CostCenter

    _require_bid_access(request.user)
    event = get_object_or_404(SourcingEvent.objects.select_related("requisition"), pk=event_id)
    services.sync_event_window_status(event=event)
    if not event.bids_visible_to_evaluators:
        messages.info(request, "Evaluation opens after the bid window closes.")
        return redirect("bid_portal_event", event_id=event.id)

    rows = build_evaluation_rows(event, request.user)
    purchase_orders = PurchaseOrder.objects.filter(sourcing_event=event).order_by("-created_at")
    return render(
        request,
        "sourcing/evaluation_event.html",
        {
            "event": event,
            "caps": sourcing_capabilities(request.user),
            "rows": rows,
            "show_commercial": event.commercial_visible_to_evaluators,
            "comparison": build_commercial_comparison(event, rows),
            "negotiation_notes": event.negotiation_notes.select_related("author", "bid__vendor"),
            "current_decision": event.award_decision,
            "decision_history": event.award_decisions.select_related(
                "winning_bid__vendor", "recommended_by", "approved_by"
            ).order_by("-created_at"),
            "purchase_orders": purchase_orders,
            "has_active_po": purchase_orders.exclude(
                status=PurchaseOrder.STATUS_CANCELLED
            ).exists(),
            "cost_centers": (
                CostCenter.objects.order_by("code")
                if event.status == SourcingEvent.STATUS_AWARDED and not event.requisition_id
                else []
            ),
            "decision_audit": get_decision_audit(event)[:100],
        },
    )
