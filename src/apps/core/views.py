from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


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
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    http_status = 200 if health_status["status"] == "healthy" else 503
    return JsonResponse(health_status, status=http_status)


class HealthAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return health_check_view(request)


def home_view(request):
    """
    Executive Dashboard page view with live aggregated ERP metrics.
    """
    from django.db.models import Avg, Count, Sum
    from apps.budgets.models import Budget, SpendLedger
    from apps.invoices.models import MatchException, SupplierInvoice
    from apps.orders.models import PurchaseOrder
    from apps.requisitions.models import PurchaseRequisition
    from apps.scorecards.models import VendorScorecard
    from apps.sourcing.models import SourcingEvent
    from apps.vendors.models import Vendor

    # Aggregate ERP Metrics
    total_pr_count = PurchaseRequisition.objects.count()
    pending_pr_count = PurchaseRequisition.objects.filter(status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]).count()
    
    total_vendors = Vendor.objects.count()
    active_vendors = Vendor.objects.filter(status="ACTIVE").count()
    kyc_review_vendors = Vendor.objects.filter(status="KYC_REVIEW").count()

    open_sourcing_events = SourcingEvent.objects.filter(status__in=["PUBLISHED", "BID_WINDOW"]).count()
    total_pos = PurchaseOrder.objects.count()
    
    total_invoices = SupplierInvoice.objects.count()
    pending_exceptions = MatchException.objects.filter(resolved=False).count()

    # Budget Aggregates
    allocated_budget = Budget.objects.aggregate(total=Sum("amount"))["total"] or 0
    committed_spend = SpendLedger.objects.filter(transaction_type="COMMITMENT").aggregate(total=Sum("amount"))["total"] or 0
    actual_spend = SpendLedger.objects.filter(transaction_type="ACTUAL").aggregate(total=Sum("amount"))["total"] or 0

    # Scorecard Aggregates
    avg_scorecard = VendorScorecard.objects.aggregate(avg=Avg("overall_score"))["avg"] or 0.0

    context = {
        "project_name": "ProcureSphere 360",
        "version": "1.0.0-DRAFT",
        "metrics": {
            "total_pr_count": total_pr_count,
            "pending_pr_count": pending_pr_count,
            "total_vendors": total_vendors,
            "active_vendors": active_vendors,
            "kyc_review_vendors": kyc_review_vendors,
            "open_sourcing_events": open_sourcing_events,
            "total_pos": total_pos,
            "total_invoices": total_invoices,
            "pending_exceptions": pending_exceptions,
            "allocated_budget": float(allocated_budget),
            "committed_spend": float(committed_spend),
            "actual_spend": float(actual_spend),
            "avg_scorecard": round(float(avg_scorecard), 1),
        },
    }
    return render(request, "pages/dashboard.html", context)
