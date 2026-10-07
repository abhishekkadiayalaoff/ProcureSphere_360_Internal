from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role
from apps.organization.models import CostCenter, Department
from apps.requisitions.models import PurchaseRequisition


@login_required(login_url="/login/")
def list_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )

    if role_code == Role.REQUESTER:
        items = PurchaseRequisition.objects.filter(requester=user).order_by("-created_at")
    elif role_code == Role.DEPT_APPROVER:
        user_department = getattr(user, "department", None)
        if user_department:
            items = PurchaseRequisition.objects.filter(department=user_department).order_by(
                "-created_at"
            )
        else:
            items = PurchaseRequisition.objects.none()
    else:
        items = PurchaseRequisition.objects.all().order_by("-created_at")

    base_layout = (
        "layouts/approver_base.html"
        if role_code in [Role.DEPT_APPROVER, Role.PROC_MGR]
        else "layouts/requester_base.html"
    )

    return render(
        request,
        "pages/requisitions/list.html",
        {"items": items, "role_code": role_code, "base_layout": base_layout},
    )


@login_required(login_url="/login/")
def create_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )
    if role_code == Role.AUDITOR:
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot create purchase requisitions.",
        )
        return redirect("requisitions_list")

    if request.method == "POST":
        title = request.POST.get("title")
        _ = request.POST.get("justification")
        department_id = request.POST.get("department")
        cost_center_id = request.POST.get("cost_center")
        requested_delivery_date = request.POST.get("requested_delivery_date")
        _ = request.FILES.getlist("attachments")

        # Simple validation
        if not (title and department_id and cost_center_id and requested_delivery_date):
            messages.error(request, "Please fill in all required fields.")
            return redirect("requisition_create")

        try:
            from apps.requisitions.services import create_purchase_requisition_service

            department = Department.objects.get(id=department_id)
            cost_center = CostCenter.objects.get(id=cost_center_id)

            # Extract Line Items
            item_descriptions = request.POST.getlist("item_description[]")
            quantities = request.POST.getlist("quantity[]")
            unit_prices = request.POST.getlist("estimated_unit_price[]")
            uoms = request.POST.getlist("unit_of_measure[]")

            line_items = []
            for i in range(len(item_descriptions)):
                desc = item_descriptions[i].strip()
                if not desc:
                    continue
                line_items.append(
                    {
                        "item_description": desc,
                        "quantity": quantities[i],
                        "estimated_unit_price": unit_prices[i],
                        "unit_of_measure": uoms[i] if i < len(uoms) else "EA",
                    }
                )

            attachments = request.FILES.getlist("attachments")

            pr = create_purchase_requisition_service(
                title=title,
                justification=request.POST.get("justification", ""),
                requester=request.user,
                department=department,
                cost_center=cost_center,
                requested_delivery_date=requested_delivery_date,
                line_items=line_items,
                attachments=attachments,
            )

            messages.success(request, f"Requisition {pr.pr_number} successfully created as DRAFT.")
            return redirect("requisition_detail", pk=pr.pk)

        except Exception as e:
            messages.error(request, f"Error creating requisition: {str(e)}")
            return redirect("requisition_create")

    if getattr(user, "department", None):
        departments = Department.objects.filter(id=user.department.id)
        cost_centers = CostCenter.objects.filter(department=user.department)
    else:
        departments = Department.objects.all()
        cost_centers = CostCenter.objects.all()

    return render(
        request,
        "pages/requisitions/create.html",
        {"departments": departments, "cost_centers": cost_centers},
    )


@login_required(login_url="/login/")
def detail_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    role_code = getattr(request.user, "role_code", None) or (
        request.user.role.code
        if hasattr(request.user, "role") and request.user.role
        else Role.SUPER_ADMIN
    )

    if role_code == Role.REQUESTER and pr.requester != request.user:
        messages.error(request, "Permission denied.")
        return redirect("requisitions_list")

    from apps.approvals.models import ApprovalAction

    approval_history = ApprovalAction.objects.filter(
        target_object_id=pr.id, target_model_name="PurchaseRequisition"
    ).order_by("created_at")

    return render(
        request,
        "pages/requisitions/detail.html",
        {"pr": pr, "role_code": role_code, "approval_history": approval_history},
    )


@login_required(login_url="/login/")
def submit_view(request, pk):
    if request.method == "POST":
        pr = get_object_or_404(PurchaseRequisition, pk=pk)
        try:
            from apps.requisitions.services import submit_purchase_requisition_service

            submit_purchase_requisition_service(requisition=pr, user=request.user)
            messages.success(request, f"Requisition {pr.pr_number} submitted to Dept Approver.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return redirect("requisition_detail", pk=pr.pk)
    return redirect("requisitions_list")


@login_required(login_url="/login/")
def approve_view(request, pk):
    if request.method == "POST":
        pr = get_object_or_404(PurchaseRequisition, pk=pk)
        try:
            from apps.requisitions.services import approve_purchase_requisition_service

            approve_purchase_requisition_service(
                requisition=pr,
                approver=request.user,
                comments=request.POST.get("comments", "Approved by Dept Approver"),
            )
            messages.success(request, f"Requisition {pr.pr_number} successfully approved.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return redirect("requisition_detail", pk=pr.pk)
    return redirect("requisitions_list")


@login_required(login_url="/login/")
def reject_view(request, pk):
    if request.method == "POST":
        pr = get_object_or_404(PurchaseRequisition, pk=pk)
        try:
            from apps.requisitions.services import reject_purchase_requisition_service

            reject_purchase_requisition_service(
                requisition=pr,
                approver=request.user,
                comments=request.POST.get("comments", "Rejected"),
            )
            messages.success(request, f"Requisition {pr.pr_number} rejected.")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
        return redirect("requisition_detail", pk=pr.pk)
    return redirect("requisitions_list")


def edit_view(*args, **kwargs):
    pass


def delete_view(*args, **kwargs):
    pass


def cancel_view(*args, **kwargs):
    pass
