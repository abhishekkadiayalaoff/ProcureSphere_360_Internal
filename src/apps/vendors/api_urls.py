from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.audit.permissions import AuditorReadOnlyPermission

from .filters import VendorFilter
from .models import Vendor, VendorCategory, VendorContact, VendorDocument, VendorRiskRecord
from .permissions import (
    VendorAccessPermission,
    can_operate_governance,
    can_view_governance,
)
from .selectors import (
    get_governance_vendor_queryset,
    get_vendor_change_history,
    get_vendor_open_transactions,
)
from .services import (
    allowed_governance_transitions,
    record_vendor_risk_assessment_service,
    register_vendor_service,
    set_vendor_status_governance_service,
)


class VendorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorCategory
        fields = ["id", "name", "code", "description"]


class VendorDocumentSerializer(serializers.ModelSerializer):
    """Never exposes the storage path; downloads go through the authorised endpoint."""

    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = VendorDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "title",
            "expiry_date",
            "is_verified",
            "created_at",
            "download_url",
        ]

    def get_download_url(self, obj) -> str:
        return f"/api/v1/vendors/{obj.vendor_id}/documents/{obj.id}/download/"


class VendorContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorContact
        fields = ["id", "first_name", "last_name", "email", "phone", "designation", "is_primary"]


class VendorRiskRecordSerializer(serializers.ModelSerializer):
    assessed_by_email = serializers.CharField(source="assessed_by.email", read_only=True)

    class Meta:
        model = VendorRiskRecord
        fields = [
            "id",
            "risk_level",
            "risk_flags",
            "assessment_notes",
            "assessed_by_email",
            "created_at",
        ]
        read_only_fields = ["id", "assessed_by_email", "created_at"]


class VendorSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    latest_risk_level = serializers.CharField(read_only=True, default=None)
    latest_composite_score = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True, default=None
    )

    class Meta:
        model = Vendor
        fields = [
            "id",
            "vendor_number",
            "legal_name",
            "trade_name",
            "tax_identification_number",
            "registration_number",
            "category",
            "category_name",
            "status",
            "status_display",
            "status_notes",
            "email",
            "phone",
            "address",
            "latest_risk_level",
            "latest_composite_score",
            "created_at",
            "updated_at",
        ]
        # Status is governed by explicit actions only.
        read_only_fields = [
            "id",
            "vendor_number",
            "status",
            "status_notes",
            "created_at",
            "updated_at",
        ]


class VendorDetailSerializer(VendorSerializer):
    documents = VendorDocumentSerializer(many=True, read_only=True)
    contacts = VendorContactSerializer(many=True, read_only=True)

    class Meta(VendorSerializer.Meta):
        fields = VendorSerializer.Meta.fields + [
            "bank_name",
            "bank_account_number",
            "bank_routing_code",
            "documents",
            "contacts",
        ]


class StatusChangePayload(serializers.Serializer):
    status = serializers.ChoiceField(choices=Vendor.STATUS_CHOICES)
    notes = serializers.CharField()


class RiskAssessmentPayload(serializers.Serializer):
    risk_level = serializers.ChoiceField(choices=VendorRiskRecord.RISK_CHOICES)
    risk_flags = serializers.ListField(
        child=serializers.ChoiceField(choices=VendorRiskRecord.RISK_FLAG_CHOICES),
        required=False,
        default=list,
    )
    notes = serializers.CharField()


class VendorViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Vendor master + governance. Vendor users see only their own record (object-level
    scoping); status changes only via POST /{id}/set-status/.
    """

    permission_classes = [VendorAccessPermission]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = VendorFilter
    ordering_fields = ["legal_name", "vendor_number", "updated_at", "created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = get_governance_vendor_queryset().prefetch_related("documents", "contacts")
        if user.is_vendor:
            return qs.filter(id=user.vendor_id) if user.vendor_id else qs.none()
        return qs

    def get_serializer_class(self):
        return VendorDetailSerializer if self.action == "retrieve" else VendorSerializer

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.instance = register_vendor_service(
            legal_name=data["legal_name"],
            tax_identification_number=data["tax_identification_number"],
            category=data["category"],
            email=data["email"],
            address=data["address"],
            trade_name=data.get("trade_name", ""),
            registration_number=data.get("registration_number", ""),
            phone=data.get("phone", ""),
            created_by_user=self.request.user,
        )

    def _require_internal_reader(self):
        if not can_view_governance(self.request.user):
            raise PermissionDenied("Vendor governance data is restricted to procurement roles.")

    @extend_schema(request=StatusChangePayload, responses=VendorSerializer)
    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        payload = StatusChangePayload(data=request.data)
        payload.is_valid(raise_exception=True)
        vendor = self.get_object()
        vendor = set_vendor_status_governance_service(
            vendor=vendor,
            actor=request.user,
            new_status=payload.validated_data["status"],
            notes=payload.validated_data["notes"],
        )
        return Response(VendorSerializer(vendor).data)

    @action(detail=True, methods=["get"], url_path="allowed-transitions")
    def allowed_transitions(self, request, pk=None):
        self._require_internal_reader()
        vendor = self.get_object()
        return Response({"allowed": allowed_governance_transitions(vendor, request.user)})

    @extend_schema(request=RiskAssessmentPayload, responses=VendorRiskRecordSerializer)
    @action(detail=True, methods=["get", "post"], url_path="risk")
    def risk(self, request, pk=None):
        self._require_internal_reader()
        vendor = self.get_object()
        if request.method == "GET":
            records = vendor.risk_records.select_related("assessed_by")
            return Response(VendorRiskRecordSerializer(records, many=True).data)
        if not can_operate_governance(request.user):
            raise PermissionDenied("Your role cannot record vendor risk assessments.")
        payload = RiskAssessmentPayload(data=request.data)
        payload.is_valid(raise_exception=True)
        record = record_vendor_risk_assessment_service(
            vendor=vendor,
            assessor=request.user,
            risk_level=payload.validated_data["risk_level"],
            risk_flags=payload.validated_data["risk_flags"],
            notes=payload.validated_data["notes"],
        )
        return Response(VendorRiskRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def documents(self, request, pk=None):
        vendor = self.get_object()  # vendor users are scoped to their own vendor
        docs = vendor.documents.order_by("-created_at")
        return Response(VendorDocumentSerializer(docs, many=True).data)

    @action(
        detail=True,
        methods=["get"],
        url_path=r"documents/(?P<doc_id>[0-9a-f-]+)/download",
    )
    def download_document(self, request, pk=None, doc_id=None):
        vendor = self.get_object()
        if not request.user.is_vendor:
            self._require_internal_reader()
        doc = get_object_or_404(VendorDocument, pk=doc_id, vendor=vendor)
        try:
            return FileResponse(doc.file.open("rb"), as_attachment=True)
        except (FileNotFoundError, ValueError):
            raise Http404("Document file is not available in storage.")

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        self._require_internal_reader()
        vendor = self.get_object()
        rows = [
            {
                "timestamp": log.timestamp,
                "actor": log.actor_email,
                "action": log.action,
                "object": log.target_model,
                "object_id": log.target_object_id,
                "previous_state": log.previous_state,
                "new_state": log.new_state,
            }
            for log in get_vendor_change_history(vendor)
        ]
        return Response(rows)

    @action(detail=True, methods=["get"], url_path="open-transactions")
    def open_transactions(self, request, pk=None):
        self._require_internal_reader()
        vendor = self.get_object()
        return Response(get_vendor_open_transactions(vendor)["summary"])

    @action(detail=True, methods=["get"])
    def scorecard(self, request, pk=None):
        from apps.scorecards.api_urls import VendorScorecardSerializer

        vendor = self.get_object()
        cards = vendor.scorecards.select_related("vendor").order_by("-created_at")
        return Response(VendorScorecardSerializer(cards, many=True).data)


class VendorCategoryViewSet(viewsets.ModelViewSet):
    queryset = VendorCategory.objects.order_by("name")
    serializer_class = VendorCategorySerializer
    permission_classes = [VendorAccessPermission, AuditorReadOnlyPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]


router = DefaultRouter()
router.register(r"categories", VendorCategoryViewSet, basename="vendor-category")
router.register(r"", VendorViewSet, basename="vendor")

urlpatterns = router.urls
