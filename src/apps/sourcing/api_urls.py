from django.db import models
from django.shortcuts import get_object_or_404
from django.urls import path
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.accounts.permissions import IsProcurementManager
from apps.audit.models import AuditLog
from apps.organization.models import Department

from .api_views import BidEvaluationViewSet, ClarificationViewSet
from .models import AwardDecision, SourcingEvent, VendorBid
from .services import evaluate_and_award_sourcing_event_service


class AwardDecisionSummarySerializer(serializers.ModelSerializer):
    winning_bid_number = serializers.CharField(source="winning_bid.bid_number", read_only=True)
    winning_vendor_name = serializers.CharField(
        source="winning_bid.vendor.legal_name", read_only=True
    )
    winning_bid_amount = serializers.DecimalField(
        source="winning_bid.total_bid_amount", max_digits=14, decimal_places=2, read_only=True
    )
    approved_by_email = serializers.CharField(source="approved_by.email", read_only=True)

    class Meta:
        model = AwardDecision
        fields = [
            "id",
            "winning_bid",
            "winning_bid_number",
            "winning_vendor_name",
            "winning_bid_amount",
            "award_reason",
            "approved_by",
            "approved_by_email",
            "created_at",
        ]


class SourcingEventSerializer(serializers.ModelSerializer):
    award_decision_summary = serializers.SerializerMethodField()
    evaluations_summary = serializers.SerializerMethodField()
    bid_count = serializers.SerializerMethodField()
    invitation_count = serializers.SerializerMethodField()
    clarifications_count = serializers.SerializerMethodField()
    unanswered_clarifications_count = serializers.SerializerMethodField()
    requisition_id = serializers.CharField(source="requisition.id", read_only=True, default=None)
    requisition_number = serializers.CharField(
        source="requisition.pr_number", read_only=True, default=None
    )
    requisition_title = serializers.CharField(
        source="requisition.title", read_only=True, default=None
    )
    department_id = serializers.CharField(
        source="requisition.department.id", read_only=True, default=None
    )
    department_name = serializers.CharField(
        source="requisition.department.name", read_only=True, default="Global / Direct"
    )
    department_code = serializers.CharField(
        source="requisition.department.code", read_only=True, default="N/A"
    )
    cost_center_code = serializers.CharField(
        source="requisition.cost_center.code", read_only=True, default="N/A"
    )
    estimated_value = serializers.DecimalField(
        source="requisition.total_amount",
        max_digits=14,
        decimal_places=2,
        read_only=True,
        default=0.0,
    )
    award_readiness = serializers.SerializerMethodField()
    award_readiness_display = serializers.SerializerMethodField()
    attention_required = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = SourcingEvent
        fields = "__all__"

    def get_award_decision_summary(self, obj):
        try:
            if hasattr(obj, "award_decision") and obj.award_decision:
                return AwardDecisionSummarySerializer(obj.award_decision).data
        except Exception:
            pass
        return None

    def get_evaluations_summary(self, obj):
        evals = obj.evaluations.all()
        if not evals.exists():
            return {"completed_count": 0, "top_weighted_score": 0.0}
        top_score = max((float(e.weighted_total_score) for e in evals), default=0.0)
        return {
            "completed_count": evals.count(),
            "top_weighted_score": round(top_score, 2),
        }

    def get_bid_count(self, obj):
        return obj.bids.count()

    def get_invitation_count(self, obj):
        return obj.invitations.count()

    def get_clarifications_count(self, obj):
        return obj.clarifications.count()

    def get_unanswered_clarifications_count(self, obj):
        return obj.clarifications.filter(status="PENDING").count()

    def get_award_readiness(self, obj):
        if obj.status == SourcingEvent.STATUS_AWARDED:
            return "AWARDED"
        if obj.status == SourcingEvent.STATUS_AWARD_APPROVAL:
            return "READY_FOR_AWARD"
        if obj.status in [
            SourcingEvent.STATUS_TECHNICAL_REVIEW,
            SourcingEvent.STATUS_COMMERCIAL_REVIEW,
        ]:
            return "READY_FOR_AWARD" if obj.evaluations.exists() else "EVALUATION_PENDING"
        if obj.status == SourcingEvent.STATUS_BID_WINDOW:
            return "BIDDING_OPEN"
        if obj.status == SourcingEvent.STATUS_CANCELLED:
            return "CANCELLED"
        if obj.status == SourcingEvent.STATUS_DRAFT:
            return "DRAFT"
        if obj.status == SourcingEvent.STATUS_PUBLISHED:
            return "PUBLISHED"
        return "NOT_READY"

    def get_award_readiness_display(self, obj):
        code = self.get_award_readiness(obj)
        labels = {
            "AWARDED": "Awarded",
            "READY_FOR_AWARD": "Ready for Award",
            "EVALUATION_PENDING": "Evaluation Pending",
            "BIDDING_OPEN": "Bidding Open",
            "DRAFT": "Draft",
            "PUBLISHED": "Published",
            "CANCELLED": "Cancelled",
            "NOT_READY": "Not Ready",
        }
        return labels.get(code, "Not Ready")

    def get_attention_required(self, obj):
        if obj.status == SourcingEvent.STATUS_AWARD_APPROVAL:
            return True
        if obj.status == SourcingEvent.STATUS_BID_WINDOW and timezone.now() > obj.bid_end_date:
            return True
        return False


class VendorBidSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.legal_name", read_only=True)
    evaluation_score = serializers.SerializerMethodField()

    class Meta:
        model = VendorBid
        fields = "__all__"

    def get_evaluation_score(self, obj):
        eval_obj = obj.evaluations.first()
        if eval_obj:
            return {
                "technical_score": float(eval_obj.technical_score),
                "commercial_score": float(eval_obj.commercial_score),
                "weighted_total_score": float(eval_obj.weighted_total_score),
                "comments": eval_obj.comments,
            }
        return None


def get_user_org(user):
    if user and user.is_authenticated and not user.is_superuser:
        if getattr(user, "department_id", None) and getattr(
            user.department, "organization_id", None
        ):
            return user.department.organization
    return None


class SourcingEventViewSet(viewsets.ModelViewSet):
    queryset = (
        SourcingEvent.objects.select_related(
            "requisition", "requisition__department", "requisition__cost_center"
        )
        .prefetch_related("invitations", "bids", "evaluations", "clarifications")
        .all()
    )
    serializer_class = SourcingEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        org = get_user_org(user)
        qs = SourcingEvent.objects.select_related(
            "requisition", "requisition__department", "requisition__cost_center"
        ).prefetch_related("invitations", "bids", "evaluations", "clarifications")

        if org:
            qs = qs.filter(
                models.Q(requisition__department__organization=org)
                | (
                    models.Q(requisition__isnull=True)
                    & models.Q(created_by__department__organization=org)
                )
            )
        return qs.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        user = request.user
        org = get_user_org(user)
        base_qs = self.get_queryset()

        active_statuses = [
            SourcingEvent.STATUS_PUBLISHED,
            SourcingEvent.STATUS_BID_WINDOW,
            SourcingEvent.STATUS_TECHNICAL_REVIEW,
            SourcingEvent.STATUS_COMMERCIAL_REVIEW,
            SourcingEvent.STATUS_AWARD_APPROVAL,
        ]
        now = timezone.now()

        total_events = base_qs.count()
        active_events = base_qs.filter(status__in=active_statuses).count()
        bidding_open = base_qs.filter(status=SourcingEvent.STATUS_BID_WINDOW).count()
        technical_review = base_qs.filter(status=SourcingEvent.STATUS_TECHNICAL_REVIEW).count()
        commercial_review = base_qs.filter(status=SourcingEvent.STATUS_COMMERCIAL_REVIEW).count()
        award_approval = base_qs.filter(status=SourcingEvent.STATUS_AWARD_APPROVAL).count()
        awarded = base_qs.filter(status=SourcingEvent.STATUS_AWARDED).count()
        cancelled = base_qs.filter(status=SourcingEvent.STATUS_CANCELLED).count()

        attention_count = base_qs.filter(
            models.Q(status=SourcingEvent.STATUS_AWARD_APPROVAL)
            | models.Q(status=SourcingEvent.STATUS_BID_WINDOW, bid_end_date__lt=now)
        ).count()

        invitations_count = sum(e.invitations.count() for e in base_qs)
        bids_count = sum(e.bids.count() for e in base_qs)

        summary_data = {
            "total_events": total_events,
            "active_events": active_events,
            "bidding_open": bidding_open,
            "technical_review": technical_review,
            "commercial_review": commercial_review,
            "award_approval": award_approval,
            "awarded": awarded,
            "cancelled": cancelled,
            "total_invited_vendors": invitations_count,
            "total_bids_received": bids_count,
            "attention_count": attention_count,
        }

        filtered_qs = base_qs

        search_query = request.GET.get("search", "").strip()
        if search_query:
            filtered_qs = filtered_qs.filter(
                models.Q(event_number__icontains=search_query)
                | models.Q(title__icontains=search_query)
                | models.Q(description__icontains=search_query)
                | models.Q(requisition__pr_number__icontains=search_query)
                | models.Q(requisition__title__icontains=search_query)
                | models.Q(requisition__department__name__icontains=search_query)
            )

        status_filter = request.GET.get("status", "").strip()
        if status_filter and status_filter != "ALL":
            filtered_qs = filtered_qs.filter(status=status_filter)

        event_type_filter = request.GET.get("event_type", "").strip()
        if event_type_filter and event_type_filter != "ALL":
            filtered_qs = filtered_qs.filter(event_type=event_type_filter)

        department_filter = request.GET.get("department", "").strip()
        if department_filter:
            filtered_qs = filtered_qs.filter(requisition__department_id=department_filter)

        readiness_filter = request.GET.get("award_readiness", "").strip()
        if readiness_filter == "READY_FOR_AWARD":
            filtered_qs = filtered_qs.filter(
                models.Q(status=SourcingEvent.STATUS_AWARD_APPROVAL)
                | models.Q(
                    status__in=[
                        SourcingEvent.STATUS_TECHNICAL_REVIEW,
                        SourcingEvent.STATUS_COMMERCIAL_REVIEW,
                    ],
                    evaluations__isnull=False,
                )
            ).distinct()
        elif readiness_filter == "EVALUATION_PENDING":
            filtered_qs = filtered_qs.filter(
                status__in=[
                    SourcingEvent.STATUS_TECHNICAL_REVIEW,
                    SourcingEvent.STATUS_COMMERCIAL_REVIEW,
                ],
                evaluations__isnull=True,
            )
        elif readiness_filter == "BIDDING_OPEN":
            filtered_qs = filtered_qs.filter(status=SourcingEvent.STATUS_BID_WINDOW)
        elif readiness_filter == "AWARDED":
            filtered_qs = filtered_qs.filter(status=SourcingEvent.STATUS_AWARDED)
        elif readiness_filter == "CANCELLED":
            filtered_qs = filtered_qs.filter(status=SourcingEvent.STATUS_CANCELLED)

        # Sorting
        sort_by = request.GET.get("sort_by", "date_desc")
        if sort_by == "date_asc":
            filtered_qs = filtered_qs.order_by("created_at")
        elif sort_by == "title_asc":
            filtered_qs = filtered_qs.order_by("title")
        elif sort_by == "status":
            filtered_qs = filtered_qs.order_by("status", "-created_at")
        else:
            filtered_qs = filtered_qs.order_by("-created_at")

        # Pagination
        try:
            page_num = max(1, int(request.GET.get("page", 1)))
        except (ValueError, TypeError):
            page_num = 1

        try:
            page_size = min(100, max(1, int(request.GET.get("page_size", 10))))
        except (ValueError, TypeError):
            page_size = 10

        from django.core.paginator import Paginator

        paginator = Paginator(filtered_qs, page_size)
        current_page_obj = paginator.get_page(page_num)

        serializer = self.get_serializer(current_page_obj, many=True)

        depts_qs = (
            Department.objects.filter(organization=org) if org else Department.objects.all()
        ).order_by("name")
        departments_data = [{"id": str(d.id), "name": d.name, "code": d.code} for d in depts_qs]

        return Response(
            {
                "summary": summary_data,
                "count": paginator.count,
                "total_count": paginator.count,
                "page": current_page_obj.number,
                "page_size": page_size,
                "total_pages": paginator.num_pages,
                "has_next": current_page_obj.has_next(),
                "has_previous": current_page_obj.has_previous(),
                "results": serializer.data,
                "departments": departments_data,
            },
            status=status.HTTP_200_OK,
        )


class VendorBidViewSet(viewsets.ModelViewSet):
    queryset = (
        VendorBid.objects.select_related("event", "vendor")
        .prefetch_related("lines", "evaluations")
        .order_by("-created_at")
    )
    serializer_class = VendorBidSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_vendor and user.vendor_id:
            return self.queryset.filter(vendor_id=user.vendor_id)

        role_code = getattr(user, "role_code", None)
        if not (
            user.is_superuser or role_code in [Role.SUPER_ADMIN, Role.PROC_MGR, Role.PROC_EXEC]
        ):
            return self.queryset.exclude(event__status=SourcingEvent.STATUS_BID_WINDOW)

        return self.queryset


class PendingAwardsAPIView(APIView):
    """
    GET /api/v1/sourcing-events/awards/pending/
    Returns sourcing events currently awaiting Manager Award Decision with evaluated vendor bids.
    """

    permission_classes = [IsAuthenticated, IsProcurementManager]

    def get(self, request):
        org = get_user_org(request.user)
        events = (
            SourcingEvent.objects.filter(
                status__in=[
                    SourcingEvent.STATUS_AWARD_APPROVAL,
                    SourcingEvent.STATUS_COMMERCIAL_REVIEW,
                    SourcingEvent.STATUS_TECHNICAL_REVIEW,
                ]
            )
            .select_related("requisition", "requisition__department", "requisition__cost_center")
            .prefetch_related(
                "bids",
                "bids__vendor",
                "evaluations",
                "evaluations__evaluator",
            )
            .order_by("-updated_at")
        )
        if org:
            events = events.filter(
                models.Q(requisition__department__organization=org)
                | (
                    models.Q(requisition__isnull=True)
                    & models.Q(created_by__department__organization=org)
                )
            )

        results = []
        for event in events:
            evaluated_bids = []
            evaluations_list = list(event.evaluations.all())
            for bid in event.bids.all():
                if bid.status not in [VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED]:
                    continue
                eval_obj = next((e for e in evaluations_list if e.bid_id == bid.id), None)
                evaluated_bids.append(
                    {
                        "bid_id": str(bid.id),
                        "bid_number": bid.bid_number,
                        "vendor_id": str(bid.vendor.id),
                        "vendor_name": bid.vendor.legal_name,
                        "total_bid_amount": float(bid.total_bid_amount),
                        "version": bid.version,
                        "submitted_at": bid.submitted_at.isoformat() if bid.submitted_at else None,
                        "technical_score": float(eval_obj.technical_score) if eval_obj else 0.0,
                        "commercial_score": float(eval_obj.commercial_score) if eval_obj else 0.0,
                        "weighted_total_score": (
                            float(eval_obj.weighted_total_score) if eval_obj else 0.0
                        ),
                        "evaluation_comments": eval_obj.comments if eval_obj else "",
                    }
                )

            evaluated_bids.sort(key=lambda b: (-b["weighted_total_score"], b["total_bid_amount"]))

            results.append(
                {
                    "id": str(event.id),
                    "event_number": event.event_number,
                    "title": event.title,
                    "event_type": event.event_type,
                    "status": event.status,
                    "description": event.description or "",
                    "requisition_id": str(event.requisition.id) if event.requisition else None,
                    "requisition_number": (
                        event.requisition.pr_number if event.requisition else None
                    ),
                    "requisition_title": (event.requisition.title if event.requisition else None),
                    "department": (
                        event.requisition.department.name
                        if event.requisition and event.requisition.department
                        else None
                    ),
                    "cost_center": (
                        event.requisition.cost_center.code
                        if event.requisition and event.requisition.cost_center
                        else None
                    ),
                    "bid_start_date": (
                        event.bid_start_date.isoformat() if event.bid_start_date else None
                    ),
                    "bid_end_date": (
                        event.bid_end_date.isoformat() if event.bid_end_date else None
                    ),
                    "bids_count": event.bids.count(),
                    "evaluations_count": event.evaluations.count(),
                    "evaluated_bids": evaluated_bids,
                    "recommended_bid": evaluated_bids[0] if evaluated_bids else None,
                }
            )

        return Response(results, status=status.HTTP_200_OK)


class AwardApproveAPIView(APIView):
    """
    POST /api/v1/sourcing-events/events/<uuid:pk>/award-approve/
    Processes Manager Award Decision (APPROVE, REJECT, or RETURN) with audit ledger logging.
    """

    permission_classes = [IsAuthenticated, IsProcurementManager]

    def post(self, request, pk):
        event = get_object_or_404(SourcingEvent, pk=pk)

        org = get_user_org(request.user)
        event_org = (
            event.requisition.department.organization
            if event.requisition and event.requisition.department
            else (
                event.created_by.department.organization
                if event.created_by and event.created_by.department
                else None
            )
        )
        if org and event_org and event_org.id != org.id:
            return Response(
                {"detail": "Permission denied: Sourcing event belongs to another organization."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if event.status == SourcingEvent.STATUS_AWARDED:
            return Response(
                {
                    "detail": f"Sourcing Event {event.event_number} is already awarded. Duplicate award approval is prevented."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if event.status not in [
            SourcingEvent.STATUS_AWARD_APPROVAL,
            SourcingEvent.STATUS_COMMERCIAL_REVIEW,
            SourcingEvent.STATUS_TECHNICAL_REVIEW,
        ]:
            return Response(
                {
                    "detail": f"Sourcing Event in status '{event.status}' cannot be awarded, rejected, or returned."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        action = str(request.data.get("action", "APPROVE")).upper()
        comments = str(request.data.get("comments", request.data.get("award_reason", ""))).strip()

        if action == "APPROVE":
            winning_bid_id = request.data.get("winning_bid_id")
            if winning_bid_id:
                winning_bid = event.bids.filter(
                    id=winning_bid_id,
                    status__in=[VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED],
                ).first()
            else:
                top_eval = event.evaluations.order_by("-weighted_total_score").first()
                if top_eval and top_eval.bid.status in [
                    VendorBid.STATUS_SUBMITTED,
                    VendorBid.STATUS_AMENDED,
                ]:
                    winning_bid = top_eval.bid
                else:
                    winning_bid = (
                        event.bids.filter(
                            status__in=[VendorBid.STATUS_SUBMITTED, VendorBid.STATUS_AMENDED]
                        )
                        .order_by("total_bid_amount")
                        .first()
                    )

            if not winning_bid:
                return Response(
                    {
                        "detail": "A valid submitted winning bid must be selected for award approval."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                decision = evaluate_and_award_sourcing_event_service(
                    event=event,
                    winning_bid=winning_bid,
                    award_reason=comments or "Award approved by Procurement Manager.",
                    approved_by_user=request.user,
                )
                return Response(
                    {
                        "message": f"Sourcing Event {event.event_number} successfully awarded to {winning_bid.vendor.legal_name}.",
                        "event_id": str(event.id),
                        "status": event.status,
                        "winning_bid_id": str(winning_bid.id),
                        "winning_vendor": winning_bid.vendor.legal_name,
                        "award_decision_id": str(decision.id),
                    },
                    status=status.HTTP_200_OK,
                )
            except Exception as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        elif action in ["REJECT", "RETURN"]:
            if not comments:
                return Response(
                    {"detail": "Rejection/return justification comments are mandatory."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            previous_status = event.status
            new_status = (
                SourcingEvent.STATUS_COMMERCIAL_REVIEW
                if action == "RETURN"
                else SourcingEvent.STATUS_CANCELLED
            )
            event.status = new_status
            event.save(update_fields=["status", "updated_at"])

            AuditLog.objects.create(
                actor=request.user,
                action=AuditLog.ACTION_REJECT if action == "REJECT" else AuditLog.ACTION_UPDATE,
                target_model="SourcingEvent",
                target_object_id=str(event.id),
                previous_state={"status": previous_status},
                new_state={"status": event.status, "action": action, "comments": comments},
            )

            return Response(
                {
                    "message": f"Sourcing Event {event.event_number} status updated to {new_status}.",
                    "event_id": str(event.id),
                    "status": event.status,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": f"Invalid action '{action}'. Supported actions: APPROVE, REJECT, RETURN."},
            status=status.HTTP_400_BAD_REQUEST,
        )


router = DefaultRouter()
router.register(r"events", SourcingEventViewSet, basename="sourcing-event")
router.register(r"bids", VendorBidViewSet, basename="vendor-bid")
router.register(r"clarifications", ClarificationViewSet, basename="sourcing-clarification")
router.register(r"evaluations", BidEvaluationViewSet, basename="bid-evaluation")

urlpatterns = [
    path("awards/pending/", PendingAwardsAPIView.as_view(), name="pending-awards-api"),
    path(
        "events/<uuid:pk>/award-approve/", AwardApproveAPIView.as_view(), name="award-approve-api"
    ),
] + router.urls
