
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.orders.models import PurchaseOrder
from apps.requisitions.models import PurchaseRequisition
from apps.scorecards.models import VendorScorecard
from apps.sourcing.models import Clarification, SourcingEvent
from apps.vendors.models import Vendor


def health_check_view(request):
    """
    Health check endpoint returning DB and Redis status.
    """
    health_status = {
        "status": "healthy",
        "service": "ProcureSphere 360",
        "database": "unknown",
        "redis": "unknown",
    }

    # Check Database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis connection
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        if redis_client.ping():
            health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = f"offline (local mode): {str(e)}"

    http_status = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=http_status)


class HealthAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return health_check_view(request)


@login_required(login_url="/login/")
def home_view(request):  # noqa: C901
    """
    Role-tailored Dashboard page view with live aggregated ERP metrics.
    Dispatches to custom workspace per user role (Requester, Approver, Procurement, Finance, Vendor, Legal, Auditor, Admin).
    """
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )

    # 1. REQUESTER ROLE DASHBOARD
    if role_code == Role.REQUESTER:
        my_prs = PurchaseRequisition.objects.filter(requester=user)
        context = {
            "metrics": {
                "total_my_prs": my_prs.count(),
                "pending_prs": my_prs.filter(
                    status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]
                ).count(),
                "approved_prs": my_prs.filter(status="APPROVED").count(),
            },
            "my_recent_prs": my_prs.order_by("-created_at")[:10],
        }
        return render(request, "pages/dashboards/requester_dashboard.html", context)

    elif role_code == Role.PROC_MGR:
        pending_prs = PurchaseRequisition.objects.filter(
            status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]
        ).order_by("-updated_at")
        open_sourcing = SourcingEvent.objects.filter(status__in=["PUBLISHED", "BID_WINDOW"]).count()
        kyc_vendors = Vendor.objects.filter(status="KYC_REVIEW")
        active_pos = PurchaseOrder.objects.filter(status="ISSUED").count()
        context = {
            "metrics": {
                "pending_approvals": pending_prs.count(),
                "open_sourcing": open_sourcing,
                "kyc_reviews": kyc_vendors.count(),
                "active_pos": active_pos,
            },
            "pending_prs": pending_prs[:5],
            "kyc_vendors": kyc_vendors[:5],
        }
        return render(request, "pages/dashboards/manager_dashboard.html", context)

    # 4. STORES / RECEIVER DASHBOARD
    elif role_code == Role.STORES_RECEIVER:
        from apps.receipts.models import GoodsReceipt, InspectionRecord, RejectionRecord

        total_grns = GoodsReceipt.objects.count()
        pending_deliveries = PurchaseOrder.objects.filter(
            status__in=["ISSUED", "ACKNOWLEDGED", "PARTIAL_RECEIPT"]
        ).count()
        total_inspections = InspectionRecord.objects.count()
        total_rejections = RejectionRecord.objects.count()
        recent_grns = GoodsReceipt.objects.select_related("po", "received_by").order_by(
            "-received_date"
        )[:10]
        context = {
            "metrics": {
                "total_grns": total_grns,
                "pending_deliveries": pending_deliveries,
                "total_inspections": total_inspections,
                "total_rejections": total_rejections,
            },
            "recent_grns": recent_grns,
        }
        return render(request, "pages/dashboards/stores_dashboard.html", context)

    # 5. VENDOR PORTAL USER DASHBOARD
    elif role_code == Role.VENDOR_USER:
        from apps.vendors.vendor_dashboard_views import vendor_dashboard_overview_view

        return vendor_dashboard_overview_view(request)

    # 6. FINANCE / AP SPECIALIST DASHBOARD
    elif role_code == Role.FINANCE_AP:
        from apps.budgets.models import SpendLedger
        from apps.invoices.models import MatchException, SupplierInvoice

        open_exceptions = MatchException.objects.filter(status=MatchException.STATUS_OPEN).order_by(
            "-created_at"
        )
        ready_for_payment = SupplierInvoice.objects.filter(
            status=SupplierInvoice.STATUS_READY_FOR_PAYMENT
        ).count()
        committed_spend = (
            SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_COMMITMENT).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        actual_spend = (
            SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_ACTUAL).aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        context = {
            "metrics": {
                "pending_exceptions": open_exceptions.count(),
                "ready_for_payment": ready_for_payment,
                "committed_spend": float(committed_spend),
                "actual_spend": float(actual_spend),
            },
            "open_exceptions": open_exceptions[:10],
        }
        return render(request, "pages/dashboards/finance_dashboard.html", context)

    # 7. PROCUREMENT EXECUTIVE DASHBOARD
    elif role_code == Role.PROC_EXEC:
        from apps.notifications.models import Notification
        from apps.sourcing.selectors import get_sourcing_dashboard_metrics
        from apps.sourcing.services import sync_all_event_windows
        from apps.vendors.filters import annotate_governance
        from apps.vendors.selectors import get_governance_metrics

        sync_all_event_windows()
        now = timezone.now()
        closing_soon = (
            SourcingEvent.objects.filter(
                status=SourcingEvent.STATUS_BID_WINDOW,
                bid_end_date__gt=now,
                bid_end_date__lte=now + timezone.timedelta(days=3),
            )
            .annotate(invite_count=Count("invitations"))
            .order_by("bid_end_date")[:8]
        )
        action_queue = SourcingEvent.objects.filter(
            status__in=[
                SourcingEvent.STATUS_DRAFT,
                SourcingEvent.STATUS_TECHNICAL_REVIEW,
                SourcingEvent.STATUS_COMMERCIAL_REVIEW,
                SourcingEvent.STATUS_AWARD_APPROVAL,
            ]
        ).order_by("-updated_at")[:10]
        attention_vendors = (
            annotate_governance(Vendor.objects.select_related("category"))
            .filter(
                Q(status=Vendor.STATUS_ON_HOLD)
                | Q(latest_risk_level="HIGH")
                | Q(latest_composite_score__lt=70)
            )
            .order_by("-updated_at")[:8]
        )
        awarded_without_po = (
            SourcingEvent.objects.filter(status=SourcingEvent.STATUS_AWARDED)
            .exclude(
                purchase_orders__status__in=[
                    PurchaseOrder.STATUS_DRAFT,
                    PurchaseOrder.STATUS_APPROVAL,
                    PurchaseOrder.STATUS_ISSUED,
                    PurchaseOrder.STATUS_ACKNOWLEDGED,
                    PurchaseOrder.STATUS_PARTIAL_RECEIPT,
                    PurchaseOrder.STATUS_COMPLETED,
                ]
            )
            .order_by("-updated_at")[:8]
        )
        avg_scorecard = VendorScorecard.objects.aggregate(avg=Avg("composite_score"))["avg"]
        context = {
            "sourcing": get_sourcing_dashboard_metrics(),
            "governance": get_governance_metrics(),
            "open_pos": PurchaseOrder.objects.filter(
                status__in=[
                    PurchaseOrder.STATUS_ISSUED,
                    PurchaseOrder.STATUS_ACKNOWLEDGED,
                    PurchaseOrder.STATUS_PARTIAL_RECEIPT,
                ]
            ).count(),
            "pending_clarifications": Clarification.objects.filter(status="PENDING")
            .exclude(event__status__in=["AWARDED", "CANCELLED"])
            .count(),
            "avg_scorecard": round(float(avg_scorecard), 1) if avg_scorecard is not None else None,
            "unread_notifications": Notification.objects.filter(
                recipient=user, is_read=False
            ).count(),
            "closing_soon": closing_soon,
            "action_queue": action_queue,
            "attention_vendors": attention_vendors,
            "awarded_without_po": awarded_without_po,
        }
        return render(request, "pages/dashboards/procurement_dashboard.html", context)

    # 8. LEGAL / CONTRACT MANAGER DASHBOARD
    elif role_code == Role.LEGAL_MGR:
        return render(request, "pages/dashboards/legal_dashboard.html")
    elif role_code == Role.FINANCE_AP:
        return render(request, "pages/dashboards/finance_dashboard.html")
    elif role_code == Role.PROC_EXEC:
        return render(request, "pages/dashboards/procurement_dashboard.html")
    elif role_code == Role.STORES_RECEIVER:
        return render(request, "pages/dashboards/stores_dashboard.html")
    elif role_code == Role.DEPT_APPROVER:
        return render(request, "pages/dashboards/approver_dashboard.html")
    elif role_code == Role.SUPER_ADMIN:
        return render(request, "pages/dashboards/superadmin_dashboard.html")
    elif role_code == Role.VENDOR_USER:
        return render(request, "pages/dashboards/vendor_dashboard.html")
    elif role_code == Role.AUDITOR:
        return render(request, "pages/dashboards/auditor_dashboard.html")

    # Fallback for all other unknown roles
    return render(request, "pages/dashboards/requester_dashboard.html")
