from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.invoices.models import MatchException, SupplierInvoice
from apps.invoices.services import (
    create_supplier_invoice_service,
    mark_invoice_paid_service,
    resolve_match_exception_service,
    run_3_way_match_service,
)
from apps.orders.models import PurchaseOrder
from apps.vendors.models import Vendor


@login_required(login_url="/login/")
def list_view(request):
    items = SupplierInvoice.objects.all().order_by("-created_at")
    return render(request, "pages/invoices/list.html", {"items": items})


@login_required(login_url="/login/")
def exceptions_list_view(request):
    exceptions = MatchException.objects.filter(status=MatchException.STATUS_OPEN).order_by(
        "-created_at"
    )
    return render(request, "pages/invoices/exceptions_list.html", {"exceptions": exceptions})


@login_required(login_url="/login/")
def exception_detail_view(request, exception_id):
    exception = get_object_or_404(MatchException, id=exception_id)
    return render(request, "pages/invoices/exception_detail.html", {"exception": exception})


@login_required(login_url="/login/")
def resolve_exception_view(request, exception_id):
    from apps.accounts.models import Role

    role_code = getattr(request.user, "role_code", None) or (
        request.user.role.code
        if hasattr(request.user, "role") and request.user.role
        else Role.SUPER_ADMIN
    )
    if role_code == Role.AUDITOR:
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot resolve invoice match exceptions.",
        )
        return redirect("exceptions_list")

    if request.method == "POST":
        exception = get_object_or_404(MatchException, id=exception_id)
        action = request.POST.get("action")  # 'RESOLVE' or 'REJECT'
        notes = request.POST.get("resolution_notes", "")

        try:
            resolve_match_exception_service(
                match_exception=exception,
                resolved_by_user=request.user,
                resolution_notes=notes,
                action=action,
            )
            messages.success(request, f"Exception successfully {action.lower()}d.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return redirect("exceptions_list")


@login_required(login_url="/login/")
def ready_for_payment_view(request):
    invoices = SupplierInvoice.objects.filter(
        status=SupplierInvoice.STATUS_READY_FOR_PAYMENT
    ).order_by("-created_at")
    return render(request, "pages/invoices/ready_list.html", {"invoices": invoices})


@login_required(login_url="/login/")
def pay_invoice_view(request, invoice_id):
    if request.method == "POST":
        invoice = get_object_or_404(SupplierInvoice, id=invoice_id)
        try:
            mark_invoice_paid_service(invoice=invoice, user=request.user)
            messages.success(
                request, f"Invoice {invoice.invoice_number} successfully marked as PAID."
            )
        except Exception as e:
            messages.error(request, f"Error paying invoice: {str(e)}")

    return redirect("ready_list")


@login_required(login_url="/login/")
def create_invoice_view(request):
    if request.method == "POST":
        vendor_id = request.POST.get("vendor_id")
        po_id = request.POST.get("po_id")
        invoice_number = request.POST.get("invoice_number")
        invoice_date = request.POST.get("invoice_date")
        due_date = request.POST.get("due_date")
        notes = request.POST.get("notes", "")

        quantity = Decimal(request.POST.get("quantity", "1.00"))
        unit_price = Decimal(request.POST.get("unit_price", "0.00"))

        try:
            vendor = get_object_or_404(Vendor, id=vendor_id)
            po = get_object_or_404(PurchaseOrder, id=po_id)
            po_line = po.lines.first()

            line_items = [
                {
                    "po_line": po_line,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "item_description": "Manual Entry Item",
                }
            ]

            invoice = create_supplier_invoice_service(
                vendor=vendor,
                po=po,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                due_date=due_date,
                line_items=line_items,
                notes=notes,
                created_by_user=request.user,
            )

            run_3_way_match_service(invoice=invoice, user=request.user)
            messages.success(request, f"Invoice {invoice_number} successfully created and matched.")
            return redirect("invoices_list")

        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")

    vendors = Vendor.objects.filter(status="ACTIVE")
    pos = PurchaseOrder.objects.filter(status__in=["ISSUED", "PARTIAL_RECEIPT", "ACKNOWLEDGED"])

    return render(request, "pages/invoices/create.html", {"vendors": vendors, "pos": pos})
