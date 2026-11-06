from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.vendors.models import Vendor
from apps.vendors.selectors import scope_vendors_queryset

from .models import VendorScorecardSLAMetric
from .permissions import can_calculate_scorecards, can_view_scorecards
from .services import calculate_vendor_scorecard_service, latest_scorecards_queryset

SORTS = {
    "score_desc": (F("composite_score").desc(nulls_last=True), "vendor__legal_name"),
    "score_asc": (F("composite_score").asc(nulls_last=True), "vendor__legal_name"),
    "vendor": ("vendor__legal_name",),
    "recent": ("-created_at",),
}


@login_required(login_url="/login/")
def scorecard_list_view(request):
    """
    Supplier Performance: latest scorecard per vendor (trend history lives on the vendor
    governance page). Scores with no underlying data are shown as "No data".
    """
    if not can_view_scorecards(request.user):
        raise PermissionDenied("Supplier scorecards are restricted to internal procurement roles.")

    qs = latest_scorecards_queryset()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(vendor__legal_name__icontains=q) | Q(vendor__vendor_number__icontains=q))
    band = request.GET.get("band", "")
    if band == "issue":
        qs = qs.filter(composite_score__lt=70)
    elif band == "watch":
        qs = qs.filter(composite_score__gte=70, composite_score__lt=85)
    elif band == "good":
        qs = qs.filter(composite_score__gte=85)
    sort = request.GET.get("sort", "score_desc")
    qs = qs.order_by(*SORTS.get(sort, SORTS["score_desc"]))

    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    can_calculate = can_calculate_scorecards(request.user)
    return render(
        request,
        "scorecards/scorecard_list.html",
        {
            "page_obj": page,
            "scorecards": page.object_list,
            "querystring": params.urlencode(),
            "q": q,
            "band": band,
            "sort": sort,
            "can_calculate": can_calculate,
            "vendors": (
                Vendor.objects.exclude(status=Vendor.STATUS_DRAFT).order_by("legal_name")
                if can_calculate
                else []
            ),
        },
    )


@login_required(login_url="/login/")
def scorecard_vendor_detail_view(request, vendor_id):
    """
    Per-vendor detailed Supplier Performance page (read-only, backend RBAC scoped):
    weighted core indicators, separate responsiveness reporting, dedicated SLA
    section with per-contract snapshots and cross-period SLA history.
    """
    if not can_view_scorecards(request.user):
        raise PermissionDenied("Supplier scorecards are restricted to internal procurement roles.")

    vendor = get_object_or_404(scope_vendors_queryset(Vendor.objects.all(), request.user), pk=vendor_id)
    cards = (
        vendor.scorecards.select_related("evaluated_by").order_by("-created_at").all()
    )
    latest = cards.first()
    sla_snapshot = (
        latest.sla_metrics.select_related("contract").all()
        if latest
        else VendorScorecardSLAMetric.objects.none()
    )
    sla_history = (
        VendorScorecardSLAMetric.objects.filter(
            scorecard__vendor=vendor, metric_code=VendorScorecardSLAMetric.MetricCodes.OVERALL
        )
        .select_related("scorecard")
        .order_by("-scorecard__created_at")
    )
    return render(
        request,
        "scorecards/scorecard_detail.html",
        {
            "vendor": vendor,
            "latest": latest,
            "scorecards": cards[:12],
            "sla_snapshot": sla_snapshot,
            "overall_row": next((r for r in sla_snapshot if r.metric_code == "OVERALL"), None),
            "contract_rows": [r for r in sla_snapshot if r.metric_code == "CONTRACT"],
            "sla_history": sla_history[:12],
        },
    )


@login_required(login_url="/login/")
@require_POST
def scorecard_calculate_view(request):
    if not can_calculate_scorecards(request.user):
        raise PermissionDenied("Your role cannot calculate supplier scorecards.")
    vendor = get_object_or_404(Vendor, pk=request.POST.get("vendor_id"))
    try:
        card = calculate_vendor_scorecard_service(
            vendor=vendor,
            evaluation_period=request.POST.get("period", ""),
            evaluated_by_user=request.user,
            comments=request.POST.get("comments", "").strip(),
        )
        if card.composite_score is None:
            messages.info(request, f"Scorecard saved for {vendor.legal_name}: no data yet.")
        else:
            messages.success(
                request,
                f"Scorecard saved for {vendor.legal_name}: composite {card.composite_score}.",
            )
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("scorecard_list")
