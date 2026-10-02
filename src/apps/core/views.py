from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.models import Avg, Count, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from redis import Redis
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.accounts.models import Role
from apps.audit.models import AuditLog
from apps.budgets.models import Budget, SpendLedger
from apps.contracts.models import Contract
from apps.invoices.models import MatchException, SupplierInvoice
from apps.orders.models import PurchaseOrder
from apps.reports.services import (
    get_contract_expiry_report,
    get_invoice_exception_aging_report,
    get_po_status_report,
    get_pr_aging_report,
    get_spend_analytics_report,
    get_supplier_performance_report,
)
from apps.requisitions.models import PurchaseRequisition
from apps.scorecards.models import VendorScorecard
from apps.sourcing.models import SourcingEvent, VendorBid
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
def home_view(request):
    """
    Role-tailored Dashboard page view with live aggregated ERP metrics.
    Dispatches to custom workspace per user role (Requester, Approver, Procurement, Finance, Vendor, Legal, Auditor, Admin).
    """
    user = request.user
    role_code = getattr(user, "role_code", None) or (user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN)

    # 1. REQUESTER ROLE DASHBOARD
    if role_code == Role.REQUESTER:
        my_prs = PurchaseRequisition.objects.filter(requester=user)
        context = {
            "metrics": {
                "total_my_prs": my_prs.count(),
                "pending_prs": my_prs.filter(status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]).count(),
                "approved_prs": my_prs.filter(status="APPROVED").count(),
            },
            "my_recent_prs": my_prs.order_by("-created_at")[:10],
        }
        return render(request, "pages/dashboards/requester_dashboard.html", context)

    # 2. DEPARTMENT APPROVER ROLE DASHBOARD
    elif role_code == Role.DEPT_APPROVER:
        pending_prs = PurchaseRequisition.objects.filter(status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]).order_by("-updated_at")
        approved_prs_count = PurchaseRequisition.objects.filter(status="APPROVED").count()
        rejected_prs_count = PurchaseRequisition.objects.filter(status="REJECTED").count()
        context = {
            "metrics": {
                "pending_count": pending_prs.count(),
                "approved_count": approved_prs_count,
                "rejected_count": rejected_prs_count,
            },
            "pending_prs": pending_prs,
        }
        return render(request, "pages/dashboards/approver_dashboard.html", context)

    # 3. PROCUREMENT MANAGER GOVERNANCE DASHBOARD
    elif role_code == Role.PROC_MGR:
        pending_prs = PurchaseRequisition.objects.filter(status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]).order_by("-updated_at")
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
        pending_deliveries = PurchaseOrder.objects.filter(status__in=["ISSUED", "ACKNOWLEDGED", "PARTIAL_RECEIPT"]).count()
        total_inspections = InspectionRecord.objects.count()
        total_rejections = RejectionRecord.objects.count()
        recent_grns = GoodsReceipt.objects.select_related("po", "received_by").order_by("-received_date")[:10]
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
        vendor = getattr(user, "vendor", None)
        vendor_pos = PurchaseOrder.objects.filter(vendor=vendor).order_by("-created_at") if vendor else PurchaseOrder.objects.none()
        active_bids = VendorBid.objects.filter(vendor=vendor).count() if vendor else 0
        total_invoices = SupplierInvoice.objects.filter(vendor=vendor).count() if vendor else 0
        context = {
            "vendor": vendor,
            "metrics": {
                "total_pos": vendor_pos.count(),
                "active_bids": active_bids,
                "total_invoices": total_invoices,
            },
            "vendor_pos": vendor_pos[:5],
        }
        return render(request, "pages/dashboards/vendor_dashboard.html", context)

    # 6. FINANCE / AP SPECIALIST DASHBOARD
    elif role_code == Role.FINANCE_AP:
        open_exceptions = MatchException.objects.filter(status=MatchException.STATUS_OPEN).order_by("-created_at")
        ready_for_payment = SupplierInvoice.objects.filter(status=SupplierInvoice.STATUS_READY_FOR_PAYMENT).count()
        committed_spend = SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_COMMITMENT).aggregate(total=Sum("amount"))["total"] or 0
        actual_spend = SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_ACTUAL).aggregate(total=Sum("amount"))["total"] or 0
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
        active_events = SourcingEvent.objects.filter(status__in=["PUBLISHED", "BID_WINDOW"]).order_by("-created_at")
        active_vendors_count = Vendor.objects.filter(status="ACTIVE").count()
        total_pos_count = PurchaseOrder.objects.count()
        avg_scorecard = VendorScorecard.objects.aggregate(avg=Avg("composite_score"))["avg"] or 0.0
        context = {
            "metrics": {
                "open_sourcing": active_events.count(),
                "active_vendors": active_vendors_count,
                "total_pos": total_pos_count,
                "avg_scorecard": round(float(avg_scorecard), 1),
            },
            "active_events": active_events,
        }
        return render(request, "pages/dashboards/procurement_dashboard.html", context)

    # 8. LEGAL / CONTRACT MANAGER DASHBOARD
    elif role_code == Role.LEGAL_MGR:
        from apps.contracts.selectors import (
            get_contracts_pending_legal_review,
            get_expiring_contracts,
            get_pending_obligations,
            get_active_contract_alerts,
            get_legal_dashboard_metrics,
        )
        active_contracts = Contract.objects.filter(status__in=[Contract.STATUS_ACTIVE, Contract.STATUS_RENEWED]).order_by("end_date")
        pending_legal = get_contracts_pending_legal_review()
        expiring_contracts = get_expiring_contracts(days=30)
        pending_obligations = get_pending_obligations()
        active_alerts = get_active_contract_alerts()
        metrics = get_legal_dashboard_metrics()

        context = {
            "metrics": metrics,
            "active_contracts_list": active_contracts[:10],
            "pending_legal_list": pending_legal[:10],
            "expiring_contracts_list": expiring_contracts[:10],
            "pending_obligations_list": pending_obligations[:10],
            "active_alerts_list": active_alerts[:10],
        }
        return render(request, "pages/dashboards/legal_dashboard.html", context)

    # 9. COMPLIANCE AUDITOR DASHBOARD
    elif role_code == Role.AUDITOR:
        total_logs = AuditLog.objects.count()
        total_approvals = AuditLog.objects.filter(action=AuditLog.ACTION_APPROVE).count()
        recent_logs = AuditLog.objects.select_related("actor").order_by("-timestamp")[:15]
        context = {
            "metrics": {
                "total_audit_logs": total_logs,
                "total_approvals": total_approvals,
            },
            "recent_logs": recent_logs,
        }
        return render(request, "pages/dashboards/auditor_dashboard.html", context)

    # 10. SUPER ADMIN / EXECUTIVE CONTROL CENTER
    total_pr_count = PurchaseRequisition.objects.count()
    pending_pr_count = PurchaseRequisition.objects.filter(status__in=["SUBMITTED", "MANAGER_REVIEW", "BUDGET_REVIEW"]).count()
    total_vendors = Vendor.objects.count()
    active_vendors = Vendor.objects.filter(status="ACTIVE").count()
    kyc_review_vendors = Vendor.objects.filter(status="KYC_REVIEW").count()
    open_sourcing_events = SourcingEvent.objects.filter(status__in=["PUBLISHED", "BID_WINDOW"]).count()
    total_pos = PurchaseOrder.objects.count()
    total_invoices = SupplierInvoice.objects.count()
    pending_exceptions = MatchException.objects.filter(status=MatchException.STATUS_OPEN).count()

    allocated_budget = Budget.objects.aggregate(total=Sum("allocated_amount"))["total"] or 0
    committed_spend = SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_COMMITMENT).aggregate(total=Sum("amount"))["total"] or 0
    actual_spend = SpendLedger.objects.filter(entry_type=SpendLedger.ENTRY_ACTUAL).aggregate(total=Sum("amount"))["total"] or 0
    avg_scorecard = VendorScorecard.objects.aggregate(avg=Avg("composite_score"))["avg"] or 0.0

    pr_data = get_pr_aging_report()
    spend_data = get_spend_analytics_report()
    po_data = get_po_status_report()
    inv_data = get_invoice_exception_aging_report()
    contract_data = get_contract_expiry_report()
    scorecard_data = get_supplier_performance_report()

    context = {
        "project_name": "ProcureSphere 360",
        "version": "1.0.0-DRAFT",
        "role_code": role_code,
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
        "dashboard_summary": {
            "total_prs": len(pr_data),
            "total_pos": len(po_data),
            "total_spend": sum(item["actual"] for item in spend_data) if spend_data else 0,
            "pending_exceptions": len([item for item in inv_data if item["status"] == "OPEN"]),
            "expiring_contracts": len([item for item in contract_data if 0 <= item["days_to_expiry"] <= 60]),
            "vendor_count": len(scorecard_data),
        },
    }
    return render(request, "pages/dashboard.html", context)
