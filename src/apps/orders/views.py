from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from apps.accounts.models import Role
from apps.orders.models import PurchaseOrder

RECEIVABLE_PO_STATUSES = [
    PurchaseOrder.STATUS_ISSUED,
    PurchaseOrder.STATUS_ACKNOWLEDGED,
    PurchaseOrder.STATUS_PARTIAL_RECEIPT,
]


@login_required(login_url="/login/")
def list_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )

    if role_code == Role.STORES_RECEIVER:
        # Stores / Receiver sees only POs eligible for receiving
        items = (
            PurchaseOrder.objects.filter(status__in=RECEIVABLE_PO_STATUSES)
            .select_related("vendor", "cost_center")
            .prefetch_related("lines")
            .order_by("-created_at")
        )
    elif role_code == Role.VENDOR_USER and getattr(user, "vendor", None):
        items = (
            PurchaseOrder.objects.filter(vendor=user.vendor)
            .select_related("vendor", "cost_center")
            .prefetch_related("lines")
            .order_by("-created_at")
        )
    else:
        items = (
            PurchaseOrder.objects.all()
            .select_related("vendor", "cost_center")
            .prefetch_related("lines")
            .order_by("-created_at")
        )

    return render(
        request,
        "pages/orders/list.html",
        {
            "items": items,
            "role_code": role_code,
            "is_stores_receiver": role_code == Role.STORES_RECEIVER,
            "receivable_statuses": RECEIVABLE_PO_STATUSES,
        },
    )


@login_required(login_url="/login/")
def detail_view(request, pk):
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )

    po = get_object_or_404(
        PurchaseOrder.objects.select_related("vendor", "cost_center", "requisition", "acknowledged_by")
        .prefetch_related("lines", "delivery_schedules", "amendments"),
        pk=pk,
    )

    # Scoping check: Stores Receiver only views receivable POs
    if role_code == Role.STORES_RECEIVER and po.status not in RECEIVABLE_PO_STATUSES:
        messages.warning(
            request,
            f"Purchase Order {po.po_number} is in '{po.get_status_display()}' status and is not currently eligible for goods receiving.",
        )
        return redirect("orders_list")

    # Scoping check: Vendor portal user can only view their own POs
    if role_code == Role.VENDOR_USER and getattr(user, "vendor", None) and po.vendor_id != user.vendor_id:
        messages.error(request, "You do not have permission to view this purchase order.")
        return redirect("orders_list")

    lines = po.lines.all()
    delivery_schedules = po.delivery_schedules.select_related("po_line").all()

    return render(
        request,
        "pages/orders/detail.html",
        {
            "po": po,
            "lines": lines,
            "delivery_schedules": delivery_schedules,
            "role_code": role_code,
            "is_stores_receiver": role_code == Role.STORES_RECEIVER,
            "is_receivable": po.status in RECEIVABLE_PO_STATUSES,
        },
    )

