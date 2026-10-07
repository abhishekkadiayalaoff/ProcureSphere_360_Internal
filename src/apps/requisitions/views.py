from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Role
from apps.approvals.models import ApprovalAction
from apps.approvals.services import process_approval_action_service
from apps.budgets.models import Budget
from apps.organization.models import CostCenter, Department
from apps.requisitions.models import PurchaseRequisition
from apps.requisitions.services import (
    create_purchase_requisition_service,
    submit_purchase_requisition_service,
)


@login_required(login_url="/login/")
def list_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )
    search_q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if role_code == Role.REQUESTER:
        items = PurchaseRequisition.objects.filter(requester=user).order_by("-created_at")
    elif role_code == Role.DEPT_APPROVER:
        user_department = getattr(user, "department", None)
        if user_department:
            items = PurchaseRequisition.objects.filter(department=user_department).order_by(
                "-created_at"
            )
        else:
            items = PurchaseRequisition.objects.all().order_by("-created_at")
    else:
        items = PurchaseRequisition.objects.all().order_by("-created_at")

    if search_q:
        items = items.filter(
            Q(pr_number__icontains=search_q)
            | Q(title__icontains=search_q)
            | Q(requester__email__icontains=search_q)
        )

    if status_filter:
        if status_filter == "PENDING":
            items = items.filter(
                status__in=[
                    PurchaseRequisition.STATUS_SUBMITTED,
                    PurchaseRequisition.STATUS_MANAGER_REVIEW,
                    PurchaseRequisition.STATUS_BUDGET_REVIEW,
                ]
            )
        elif status_filter == "APPROVED":
            items = items.filter(
                status__in=[
                    PurchaseRequisition.STATUS_APPROVED,
                    PurchaseRequisition.STATUS_SOURCING,
                    PurchaseRequisition.STATUS_PO_ISSUED,
                ]
            )
        else:
            items = items.filter(status=status_filter)

    if role_code == Role.LEGAL_MGR or role_code == "LEGAL_MGR":
        base_layout = "layouts/legal_base.html"
    elif role_code in [Role.DEPT_APPROVER, Role.PROC_MGR]:
        base_layout = "layouts/approver_base.html"
    else:
        base_layout = "layouts/requester_base.html"

    return render(
        request,
        "pages/requisitions/list.html",
        {
            "items": items,
            "role_code": role_code,
            "base_layout": base_layout,
            "search_q": search_q,
            "status_filter": status_filter,
        },
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
        title = request.POST.get("title", "").strip()
        justification = request.POST.get("justification", "").strip()
        department_id = request.POST.get("department")
        cost_center_id = request.POST.get("cost_center")
        requested_delivery_date = request.POST.get("requested_delivery_date")
        attachments = request.FILES.getlist("attachments")
        action_type = request.POST.get("action_type", "save_draft")

        if not (title and department_id and cost_center_id and requested_delivery_date):
            messages.error(request, "Please fill in all required fields.")
            return redirect("requisition_create")

        try:
            dept = Department.objects.get(id=department_id)
            cost_ctr = CostCenter.objects.get(id=cost_center_id)

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

            if not line_items:
                messages.error(request, "Please add at least one line item.")
                return redirect("requisition_create")

            pr = create_purchase_requisition_service(
                title=title,
                justification=justification,
                requester=user,
                department=dept,
                cost_center=cost_ctr,
                requested_delivery_date=requested_delivery_date,
                line_items=line_items,
                attachments=attachments,
            )

            if action_type == "submit" or "submit" in request.POST:
                submit_purchase_requisition_service(requisition=pr, user=user)
                messages.success(
                    request,
                    f"Purchase Requisition {pr.pr_number} created and submitted for approval successfully!",
                )
            else:
                messages.success(request, f"Purchase Requisition {pr.pr_number} created in Draft status.")

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
    user = request.user
    role_code = getattr(user, "role_code", None) or (
        user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN
    )
    pr = get_object_or_404(
        PurchaseRequisition.objects.select_related("requester", "department", "cost_center").prefetch_related(
            "lines", "attachments", "purchase_orders"
        ),
        pk=pk,
    )

    approval_history = (
        ApprovalAction.objects.filter(target_object_id=str(pr.id))
        .select_related("actor")
        .order_by("-created_at")
    )

    budget = Budget.objects.filter(cost_center=pr.cost_center).first()
    available_budget = budget.available_amount if budget else None

    if role_code == Role.LEGAL_MGR or role_code == "LEGAL_MGR":
        base_layout = "layouts/legal_base.html"
    elif role_code in [Role.DEPT_APPROVER, Role.PROC_MGR]:
        base_layout = "layouts/approver_base.html"
    else:
        base_layout = "layouts/requester_base.html"

    return render(
        request,
        "pages/requisitions/detail.html",
        {
            "pr": pr,
            "approval_history": approval_history,
            "available_budget": available_budget,
            "base_layout": base_layout,
            "role_code": role_code,
        },
    )


@login_required(login_url="/login/")
def submit_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if request.method == "POST":
        try:
            submit_purchase_requisition_service(requisition=pr, user=request.user)
            messages.success(
                request, f"Requisition {pr.pr_number} successfully submitted for approval!"
            )
        except Exception as e:
            messages.error(request, f"Submission error: {str(e)}")
    return redirect("requisition_detail", pk=pr.pk)


@login_required(login_url="/login/")
def approve_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if request.method == "POST":
        comments = request.POST.get("comments", "").strip()
        try:
            process_approval_action_service(
                target_object=pr, actor=request.user, action="APPROVED", comments=comments
            )
            messages.success(request, f"Requisition {pr.pr_number} approved successfully!")
        except Exception as e:
            messages.error(request, f"Approval error: {str(e)}")
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)
    return redirect("requisition_detail", pk=pr.pk)


@login_required(login_url="/login/")
def reject_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if request.method == "POST":
        comments = request.POST.get("comments", "").strip() or "Rejected by Approver."
        try:
            process_approval_action_service(
                target_object=pr, actor=request.user, action="REJECTED", comments=comments
            )
            messages.success(request, f"Requisition {pr.pr_number} rejected.")
        except Exception as e:
            messages.error(request, f"Rejection error: {str(e)}")
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)
    return redirect("requisition_detail", pk=pr.pk)


@login_required(login_url="/login/")
def edit_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if pr.status != PurchaseRequisition.STATUS_DRAFT:
        messages.error(request, "Only draft requisitions can be edited.")
        return redirect("requisition_detail", pk=pr.pk)

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        justification = request.POST.get("justification", "").strip()
        requested_delivery_date = request.POST.get("requested_delivery_date")

        if title:
            pr.title = title
        if justification:
            pr.justification = justification
        if requested_delivery_date:
            pr.requested_delivery_date = requested_delivery_date
        pr.save()

        messages.success(request, f"Requisition {pr.pr_number} updated successfully.")
        return redirect("requisition_detail", pk=pr.pk)

    return render(
        request,
        "pages/requisitions/edit.html",
        {
            "pr": pr,
            "departments": Department.objects.all(),
            "cost_centers": CostCenter.objects.all(),
        },
    )


@login_required(login_url="/login/")
def cancel_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if request.method == "POST":
        if pr.status in [
            PurchaseRequisition.STATUS_DRAFT,
            PurchaseRequisition.STATUS_SUBMITTED,
            PurchaseRequisition.STATUS_MANAGER_REVIEW,
            PurchaseRequisition.STATUS_BUDGET_REVIEW,
        ]:
            pr.status = PurchaseRequisition.STATUS_CANCELLED
            pr.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Requisition {pr.pr_number} has been cancelled.")
        else:
            messages.error(request, f"Cannot cancel requisition in status '{pr.status}'.")
    return redirect("requisition_detail", pk=pr.pk)


@login_required(login_url="/login/")
def delete_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if pr.status == PurchaseRequisition.STATUS_DRAFT and pr.requester == request.user:
        pr.delete()
        messages.success(request, "Draft requisition deleted successfully.")
        return redirect("requisitions_list")
    messages.error(request, "Cannot delete requisition.")
    return redirect("requisition_detail", pk=pr.pk)
