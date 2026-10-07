from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.vendors.models import Vendor

from .models import VendorScorecard
from .permissions import can_calculate_scorecards, can_view_scorecards
from .services import calculate_vendor_scorecard_service


class VendorScorecardSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.legal_name", read_only=True)

    class Meta:
        model = VendorScorecard
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "evaluation_period",
            "delivery_score",
            "quality_score",
            "price_score",
            "responsiveness_score",
            "compliance_score",
            "sla_score",
            "composite_score",
            "evaluator_comments",
            "created_at",
        ]
        read_only_fields = fields


class CalculatePayload(serializers.Serializer):
    vendor_id = serializers.UUIDField()
    period = serializers.CharField(max_length=50)
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class VendorScorecardViewSet(viewsets.ReadOnlyModelViewSet):
    """Scorecards are computed by the service, never written directly."""

    serializer_class = VendorScorecardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = VendorScorecard.objects.select_related("vendor", "evaluated_by").order_by(
            "-created_at"
        )
        if user.is_vendor:
            return qs.filter(vendor_id=user.vendor_id) if user.vendor_id else qs.none()
        if not can_view_scorecards(user):
            return qs.none()
        vendor_id = self.request.query_params.get("vendor")
        return qs.filter(vendor_id=vendor_id) if vendor_id else qs

    @action(detail=False, methods=["post"], url_path="calculate")
    def calculate(self, request):
        if not can_calculate_scorecards(request.user):
            raise PermissionDenied("Your role cannot calculate supplier scorecards.")
        payload = CalculatePayload(data=request.data)
        payload.is_valid(raise_exception=True)
        vendor = get_object_or_404(Vendor, pk=payload.validated_data["vendor_id"])
        scorecard = calculate_vendor_scorecard_service(
            vendor=vendor,
            evaluation_period=payload.validated_data["period"],
            evaluated_by_user=request.user,
            comments=payload.validated_data["comments"],
        )
        return Response(VendorScorecardSerializer(scorecard).data, status=status.HTTP_201_CREATED)


router = DefaultRouter()
router.register(r"", VendorScorecardViewSet, basename="scorecard")

urlpatterns = router.urls
