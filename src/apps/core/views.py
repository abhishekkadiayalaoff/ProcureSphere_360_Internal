
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.requisitions.models import PurchaseRequisition


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
        return render(request, "pages/dashboards/manager_dashboard.html")
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
