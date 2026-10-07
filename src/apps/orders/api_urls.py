from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter

from apps.accounts.permissions import IsProcurementManager
from apps.audit.permissions import AuditorReadOnlyPermission
from apps.invoices.models import SupplierInvoice

from .models import DeliverySchedule, POAmendment, POLine, PurchaseOrder
from .services import cancel_purchase_order_governance_service


class POLineSerializer(serializers.ModelSerializer):
    remaining_quantity = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = POLine
        fields = [
            "id",
            "item_description",
            "quantity",
            "quantity_received",
            "remaining_quantity",
            "unit_of_measure",
            "unit_price",
            "line_total",
            "created_at",
            "updated_at",
        ]


class POAmendmentSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.CharField(source="requested_by.email", read_only=True)

    class Meta:
        model = POAmendment
        fields = [
            "id",
            "amendment_number",
            "reason",
            "previous_version_snapshot",
            "requested_by",
            "requested_by_email",
            "created_at",
        ]


class DeliveryScheduleSerializer(serializers.ModelSerializer):
    line_description = serializers.CharField(source="po_line.item_description", read_only=True)

    class Meta:
        model = DeliverySchedule
        fields = [
            "id",
            "po_line",
            "line_description",
            "expected_delivery_date",
            "quantity_expected",
            "destination_address",
            "status",
            "created_at",
        ]


class POInvoiceSummarySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SupplierInvoice
        fields = [
            "id",
            "invoice_number",
            "invoice_date",
            "due_date",
            "status",
            "status_display",
            "subtotal",
            "tax_amount",
            "total_amount",
            "created_at",
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    lines = POLineSerializer(many=True, read_only=True)
    amendments = POAmendmentSerializer(many=True, read_only=True)
    delivery_schedules = DeliveryScheduleSerializer(many=True, read_only=True)
    invoices = POInvoiceSummarySerializer(many=True, read_only=True)

    vendor_name = serializers.CharField(source="vendor.legal_name", read_only=True)
    vendor_number = serializers.CharField(source="vendor.vendor_number", read_only=True)
    vendor_status = serializers.CharField(source="vendor.status", read_only=True)
    vendor_risk_level = serializers.SerializerMethodField()

    cost_center_code = serializers.CharField(source="cost_center.code", read_only=True)
    department_id = serializers.CharField(source="cost_center.department.id", read_only=True)
    department_name = serializers.CharField(source="cost_center.department.name", read_only=True)
    department_code = serializers.CharField(source="cost_center.department.code", read_only=True)

    requisition_number = serializers.CharField(source="requisition.requisition_number", read_only=True)
    sourcing_title = serializers.CharField(source="sourcing_event.title", read_only=True)

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    acknowledged_by_email = serializers.CharField(source="acknowledged_by.email", read_only=True)
    is_acknowledged = serializers.SerializerMethodField()

    lines_count = serializers.SerializerMethodField()
    total_quantity_ordered = serializers.SerializerMethodField()
    total_quantity_received = serializers.SerializerMethodField()
    fulfillment_percentage = serializers.SerializerMethodField()
    delivery_schedules_count = serializers.SerializerMethodField()
    invoices_count = serializers.SerializerMethodField()
    amendments_count = serializers.SerializerMethodField()
    latest_amendment_reason = serializers.SerializerMethodField()
    latest_amendment_date = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "po_number",
            "version",
            "status",
            "status_display",
            "vendor",
            "vendor_name",
            "vendor_number",
            "vendor_status",
            "vendor_risk_level",
            "cost_center",
            "cost_center_code",
            "department_id",
            "department_name",
            "department_code",
            "requisition",
            "requisition_number",
            "sourcing_event",
            "sourcing_title",
            "subtotal",
            "tax_amount",
            "total_amount",
            "terms_and_conditions",
            "acknowledged_at",
            "acknowledged_by",
            "acknowledged_by_email",
            "acknowledgement_notes",
            "is_acknowledged",
            "lines_count",
            "total_quantity_ordered",
            "total_quantity_received",
            "fulfillment_percentage",
            "delivery_schedules_count",
            "invoices_count",
            "amendments_count",
            "latest_amendment_reason",
            "latest_amendment_date",
            "created_at",
            "updated_at",
            "lines",
            "amendments",
            "delivery_schedules",
            "invoices",
        ]

    def get_vendor_risk_level(self, obj):
        latest_risk = obj.vendor.risk_records.order_by("-created_at").first()
        return latest_risk.risk_level if latest_risk else "LOW"

    def get_is_acknowledged(self, obj):
        return bool(obj.acknowledged_at or obj.status == PurchaseOrder.STATUS_ACKNOWLEDGED)

    def get_lines_count(self, obj):
        return obj.lines.count()

    def get_total_quantity_ordered(self, obj):
        total = sum((line.quantity for line in obj.lines.all()), Decimal("0.00"))
        return float(total)

    def get_total_quantity_received(self, obj):
        total = sum((line.quantity_received or Decimal("0.00") for line in obj.lines.all()), Decimal("0.00"))
        return float(total)

    def get_fulfillment_percentage(self, obj):
        lines = list(obj.lines.all())
        if not lines:
            return 100.0 if obj.status == PurchaseOrder.STATUS_COMPLETED else 0.0
        total_ordered = sum((l.quantity for l in lines), Decimal("0.00"))
        total_received = sum((l.quantity_received or Decimal("0.00") for l in lines), Decimal("0.00"))
        if total_ordered <= Decimal("0.00"):
            return 100.0 if obj.status == PurchaseOrder.STATUS_COMPLETED else 0.0
        pct = (total_received / total_ordered) * Decimal("100.0")
        return min(100.0, round(float(pct), 1))

    def get_delivery_schedules_count(self, obj):
        return obj.delivery_schedules.count()

    def get_invoices_count(self, obj):
        return obj.invoices.count()

    def get_amendments_count(self, obj):
        return obj.amendments.count()

    def get_latest_amendment_reason(self, obj):
        latest = obj.amendments.order_by("-amendment_number").first()
        return latest.reason if latest else ""

    def get_latest_amendment_date(self, obj):
        latest = obj.amendments.order_by("-amendment_number").first()
        return latest.created_at.isoformat() if latest else None


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseOrder.objects.select_related(
            "vendor",
            "cost_center",
            "cost_center__department",
            "cost_center__department__organization",
            "requisition",
            "sourcing_event",
            "acknowledged_by",
        )
        .prefetch_related(
            "lines",
            "amendments",
            "amendments__requested_by",
            "delivery_schedules",
            "delivery_schedules__po_line",
            "invoices",
            "vendor__risk_records",
        )
        .order_by("-created_at")
    )
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, AuditorReadOnlyPermission]
    filterset_fields = ["status", "vendor", "cost_center"]
    search_fields = ["po_number", "vendor__legal_name", "terms_and_conditions", "lines__item_description"]
    ordering_fields = ["created_at", "total_amount", "po_number", "version", "status"]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset

        # Vendor scoping
        if getattr(user, "is_vendor", False) or getattr(user, "vendor_id", None):
            if getattr(user, "vendor_id", None):
                qs = qs.filter(vendor_id=user.vendor_id)
            else:
                return qs.none()

        # Tenant/Organization scoping for internal non-superusers
        if (
            not user.is_superuser
            and getattr(user, "department_id", None)
            and getattr(user.department, "organization_id", None)
        ):
            qs = qs.filter(cost_center__department__organization=user.department.organization)

        # Filter by search param
        search_query = self.request.query_params.get("search", "").strip()
        if search_query:
            qs = qs.filter(
                Q(po_number__icontains=search_query)
                | Q(vendor__legal_name__icontains=search_query)
                | Q(terms_and_conditions__icontains=search_query)
                | Q(lines__item_description__icontains=search_query)
            ).distinct()

        # Filter by status query param
        status_param = self.request.query_params.get("status", "").strip().upper()
        if status_param:
            qs = qs.filter(status=status_param)

        # Filter by acknowledgement_status query param
        ack_param = self.request.query_params.get("acknowledgement_status", "").strip().lower()
        if ack_param == "acknowledged":
            qs = qs.filter(Q(acknowledged_at__isnull=False) | Q(status=PurchaseOrder.STATUS_ACKNOWLEDGED))
        elif ack_param == "pending":
            qs = qs.filter(
                acknowledged_at__isnull=True,
                status__in=[
                    PurchaseOrder.STATUS_ISSUED,
                    PurchaseOrder.STATUS_DRAFT,
                    PurchaseOrder.STATUS_APPROVAL,
                ],
            )

        # Filter by vendor query param
        vendor_param = self.request.query_params.get("vendor", "").strip()
        if vendor_param:
            qs = qs.filter(vendor_id=vendor_param)

        # Filter by cost_center query param
        cost_center_param = self.request.query_params.get("cost_center", "").strip()
        if cost_center_param:
            qs = qs.filter(cost_center_id=cost_center_param)

        # Filter by department query param
        department_param = self.request.query_params.get("department", "").strip()
        if department_param:
            qs = qs.filter(
                Q(cost_center__department_id=department_param)
                | Q(cost_center__department__code__iexact=department_param)
            )

        # Filter by has_amendments query param
        has_amendments = self.request.query_params.get("has_amendments", "").strip().lower()
        if has_amendments in ["true", "1", "yes"]:
            qs = qs.filter(amendments__isnull=False).distinct()
        elif has_amendments in ["false", "0", "no"]:
            qs = qs.filter(amendments__isnull=True)

        # Sorting
        sort_by = self.request.query_params.get("sort_by", "").strip()
        if sort_by:
            allowed_sorts = [
                "created_at",
                "-created_at",
                "total_amount",
                "-total_amount",
                "po_number",
                "-po_number",
                "version",
                "-version",
                "status",
                "-status",
            ]
            if sort_by in allowed_sorts:
                qs = qs.order_by(sort_by)

        return qs

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/v1/purchase-orders/summary/
        Returns comprehensive KPI metrics for the Purchase Orders Governance Desk.
        """
        qs = self.get_queryset()

        total_pos = qs.count()
        total_value_data = qs.aggregate(total=Sum("total_amount"))
        total_po_value = float(total_value_data["total"] or Decimal("0.00"))

        status_counts = dict(qs.values_list("status").annotate(count=Count("id")))
        issued_count = status_counts.get(PurchaseOrder.STATUS_ISSUED, 0)
        acknowledged_count = status_counts.get(PurchaseOrder.STATUS_ACKNOWLEDGED, 0)
        partial_receipt_count = status_counts.get(PurchaseOrder.STATUS_PARTIAL_RECEIPT, 0)
        completed_count = status_counts.get(PurchaseOrder.STATUS_COMPLETED, 0)
        cancelled_count = status_counts.get(PurchaseOrder.STATUS_CANCELLED, 0)
        draft_count = status_counts.get(PurchaseOrder.STATUS_DRAFT, 0)
        approval_count = status_counts.get(PurchaseOrder.STATUS_APPROVAL, 0)

        # Pending Acknowledgements
        pending_ack_count = qs.filter(
            status=PurchaseOrder.STATUS_ISSUED, acknowledged_at__isnull=True
        ).count()

        # Active commitments value (ISSUED, ACKNOWLEDGED, PARTIAL_RECEIPT)
        active_commitments_data = qs.filter(
            status__in=[
                PurchaseOrder.STATUS_ISSUED,
                PurchaseOrder.STATUS_ACKNOWLEDGED,
                PurchaseOrder.STATUS_PARTIAL_RECEIPT,
            ]
        ).aggregate(total=Sum("total_amount"))
        active_commitments_value = float(active_commitments_data["total"] or Decimal("0.00"))

        # Amended orders count
        amended_orders_count = qs.filter(amendments__isnull=False).distinct().count()

        return Response(
            {
                "total_pos": total_pos,
                "total_po_value": total_po_value,
                "active_commitments_value": active_commitments_value,
                "issued_count": issued_count,
                "acknowledged_count": acknowledged_count,
                "pending_acknowledgement_count": pending_ack_count,
                "partial_receipt_count": partial_receipt_count,
                "completed_count": completed_count,
                "cancelled_count": cancelled_count,
                "draft_count": draft_count,
                "approval_count": approval_count,
                "has_amendments_count": amended_orders_count,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="governance-cancel",
        permission_classes=[IsAuthenticated, IsProcurementManager],
    )
    def governance_cancel(self, request, pk=None):
        """
        POST /api/v1/purchase-orders/<uuid:pk>/governance-cancel/
        Manager governance action to cancel a PO and release remaining budget commitment.
        """
        po = self.get_object()
        reason = str(request.data.get("reason", request.data.get("justification", ""))).strip()

        if not reason:
            return Response(
                {"detail": "Cancellation justification reason is mandatory."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            updated_po = cancel_purchase_order_governance_service(
                po=po, actor=request.user, reason=reason
            )
            serializer = self.get_serializer(updated_po)
            return Response(
                {
                    "message": f"Purchase Order {po.po_number} successfully cancelled. Financial commitments released.",
                    "purchase_order": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


router = DefaultRouter()
router.register(r"", PurchaseOrderViewSet, basename="purchase-order")

urlpatterns = router.urls
