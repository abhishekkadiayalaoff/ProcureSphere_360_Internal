from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from apps.requisitions.models import PurchaseRequisition, PRLine
from apps.organization.models import Department, CostCenter
from apps.accounts.models import Role

@login_required(login_url="/login/")
def list_view(request):
    user = request.user
    role_code = getattr(user, "role_code", None) or (user.role.code if hasattr(user, "role") and user.role else Role.SUPER_ADMIN)
    
    if role_code == Role.REQUESTER:
        items = PurchaseRequisition.objects.filter(requester=user).order_by("-created_at")
    elif role_code == Role.DEPT_APPROVER and getattr(user, "department", None):
        items = PurchaseRequisition.objects.filter(department=user.department).order_by("-created_at")
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
        {"items": items, "role_code": role_code, "base_layout": base_layout}
    )

@login_required(login_url="/login/")
def create_view(request):
    user = request.user
    
    if request.method == "POST":
        title = request.POST.get("title")
        justification = request.POST.get("justification")
        department_id = request.POST.get("department")
        cost_center_id = request.POST.get("cost_center")
        requested_delivery_date = request.POST.get("requested_delivery_date")
        attachments = request.FILES.getlist("attachments")
        
        # Simple validation
        if not (title and department_id and cost_center_id and requested_delivery_date):
            messages.error(request, "Please fill in all required fields.")
            return redirect("requisition_create")

        try:
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
                line_items.append({
                    "item_description": desc,
                    "quantity": quantities[i],
                    "estimated_unit_price": unit_prices[i],
                    "unit_of_measure": uoms[i] if i < len(uoms) else "EA"
                })
                
            from apps.requisitions.services import create_purchase_requisition_service
            pr = create_purchase_requisition_service(
                title=title,
                justification=justification,
                requester=user,
                department=department,
                cost_center=cost_center,
                requested_delivery_date=requested_delivery_date,
                line_items=line_items,
                attachments=attachments
            )
                
            submit_action = request.POST.get("submit_action", "draft")
            if submit_action == "submit":
                from apps.requisitions.services import submit_purchase_requisition_service
                submit_purchase_requisition_service(requisition=pr, user=user)
                messages.success(request, f"Requisition {pr.pr_number} created and submitted for Department Approval!")
            else:
                messages.success(request, f"Requisition {pr.pr_number} created successfully as Draft.")

            return redirect("requisition_detail", pk=pr.pk)
        except Exception as e:
            messages.error(request, f"Error creating requisition: {str(e)}")
            return redirect("requisition_create")

    # GET Request
    if request.user.department:
        departments = Department.objects.filter(id=request.user.department.id)
        cost_centers = CostCenter.objects.filter(department=request.user.department)
    else:
        departments = Department.objects.all()
        cost_centers = CostCenter.objects.all()

    cost_centers = _attach_available_budgets(cost_centers)
        
    return render(
        request, 
        "pages/requisitions/create.html", 
        {"departments": departments, "cost_centers": cost_centers}
    )

def _attach_available_budgets(cost_centers):
    from apps.budgets.models import Budget
    from django.utils import timezone
    today = timezone.now().date()

    budgets = Budget.objects.filter(
        cost_center__in=cost_centers,
        fiscal_period__start_date__lte=today,
        fiscal_period__end_date__gte=today,
        fiscal_period__is_closed=False,
    )
    budget_map = {b.cost_center_id: b.available_amount for b in budgets}
    cc_list = []
    for cc in cost_centers:
        cc.available_budget = budget_map.get(cc.id, None)
        cc_list.append(cc)
    return cc_list

@login_required(login_url="/login/")
def edit_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    if pr.requester != request.user:
        messages.error(request, "You do not have permission to edit this requisition.")
        return redirect("requisitions_list")
        
    if pr.status != PurchaseRequisition.STATUS_DRAFT:
        messages.error(request, "Only draft requisitions can be edited.")
        return redirect("requisition_detail", pk=pr.pk)
        
    if request.method == "POST":
        title = request.POST.get("title")
        justification = request.POST.get("justification")
        department_id = request.POST.get("department")
        cost_center_id = request.POST.get("cost_center")
        requested_delivery_date = request.POST.get("requested_delivery_date")
        attachments = request.FILES.getlist("attachments")
        
        try:
            department = Department.objects.get(id=department_id)
            cost_center = CostCenter.objects.get(id=cost_center_id)
            
            # Update basic fields
            pr.title = title
            pr.justification = justification
            pr.department = department
            pr.cost_center = cost_center
            pr.requested_delivery_date = requested_delivery_date
            
            # Extract Line Items
            item_descriptions = request.POST.getlist("item_description[]")
            quantities = request.POST.getlist("quantity[]")
            unit_prices = request.POST.getlist("estimated_unit_price[]")
            uoms = request.POST.getlist("unit_of_measure[]")
            
            with transaction.atomic():
                # Delete existing lines and recreate
                pr.lines.all().delete()
                
                total_amount = 0
                for i in range(len(item_descriptions)):
                    desc = item_descriptions[i].strip()
                    if not desc:
                        continue
                        
                    qty = float(quantities[i])
                    price = float(unit_prices[i])
                    uom = uoms[i]
                    
                    line = PRLine.objects.create(
                        requisition=pr,
                        item_description=desc,
                        quantity=qty,
                        unit_of_measure=uom,
                        estimated_unit_price=price
                    )
                    total_amount += (qty * price)
                    
                # Validate budget before saving PR total
                from apps.budgets.services import validate_budget_availability_service
                from decimal import Decimal
                validate_budget_availability_service(cost_center=cost_center, amount=Decimal(str(total_amount)))

                pr.total_amount = total_amount
                pr.save()
                
                if attachments:
                    from apps.requisitions.models import PRAttachment
                    for uploaded_file in attachments:
                        PRAttachment.objects.create(
                            requisition=pr,
                            title=uploaded_file.name,
                            file=uploaded_file
                        )
                
            messages.success(request, f"Requisition {pr.pr_number} updated successfully.")
            return redirect("requisition_detail", pk=pr.pk)
        except Exception as e:
            messages.error(request, f"Error updating requisition: {str(e)}")
            
    # GET Request
    if request.user.department:
        departments = Department.objects.filter(id=request.user.department.id)
        cost_centers = CostCenter.objects.filter(department=request.user.department)
    else:
        departments = Department.objects.all()
        cost_centers = CostCenter.objects.all()

    cost_centers = _attach_available_budgets(cost_centers)
        
    return render(
        request, 
        "pages/requisitions/edit.html", 
        {"pr": pr, "departments": departments, "cost_centers": cost_centers}
    )

@login_required(login_url="/login/")
def detail_view(request, pk):
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    # Simple object-level security
    role_code = getattr(request.user, "role_code", None) or (request.user.role.code if hasattr(request.user, "role") and request.user.role else Role.SUPER_ADMIN)
    if role_code == Role.REQUESTER and pr.requester != request.user:
        messages.error(request, "You do not have permission to view this requisition.")
        return redirect("requisitions_list")
        
    from apps.approvals.models import ApprovalAction
    approval_history = ApprovalAction.objects.filter(
        target_object_id=pr.id,
        target_model_name="PurchaseRequisition"
    ).order_by("created_at")

    from apps.budgets.models import Budget
    from django.utils import timezone
    today = timezone.now().date()
    active_budget = Budget.objects.filter(
        cost_center=pr.cost_center,
        fiscal_period__start_date__lte=today,
        fiscal_period__end_date__gte=today,
        fiscal_period__is_closed=False,
    ).first()
    available_budget = active_budget.available_amount if active_budget else None
        
    base_layout = (
        "layouts/approver_base.html"
        if role_code in [Role.DEPT_APPROVER, Role.PROC_MGR]
        else "layouts/requester_base.html"
    )

    return render(
        request,
        "pages/requisitions/detail.html",
        {
            "pr": pr, 
            "role_code": role_code,
            "approval_history": approval_history,
            "available_budget": available_budget,
            "base_layout": base_layout,
        }
    )

@login_required(login_url="/login/")
def submit_view(request, pk):
    if request.method != "POST":
        return redirect("requisitions_list")
        
    pr = get_object_or_404(PurchaseRequisition, pk=pk)
    
    # Check permissions
    if pr.requester != request.user:
        messages.error(request, "You do not have permission to submit this requisition.")
        return redirect("requisition_detail", pk=pr.pk)
        
    if pr.status != PurchaseRequisition.STATUS_DRAFT:
        messages.error(request, "Only draft requisitions can be submitted.")
        return redirect("requisition_detail", pk=pr.pk)
        
    # Use service function for workflow transitions
    try:
        from apps.requisitions.services import submit_purchase_requisition_service
        submit_purchase_requisition_service(requisition=pr, user=request.user)
        messages.success(request, f"Requisition {pr.pr_number} submitted successfully.")
    except Exception as e:
        messages.error(request, f"Error submitting requisition: {str(e)}")
        
    return redirect("requisition_detail", pk=pr.pk)

@login_required(login_url="/login/")
def cancel_view(request, pk):
    if request.method == "POST":
        pr = get_object_or_404(PurchaseRequisition, pk=pk)
        
        if pr.requester != request.user:
            messages.error(request, "You do not have permission to cancel this requisition.")
            return redirect("requisition_detail", pk=pr.pk)
            
        allowed_cancel_statuses = [
            PurchaseRequisition.STATUS_DRAFT,
            PurchaseRequisition.STATUS_SUBMITTED,
            PurchaseRequisition.STATUS_MANAGER_REVIEW,
            PurchaseRequisition.STATUS_BUDGET_REVIEW
        ]
        
        if pr.status not in allowed_cancel_statuses:
            messages.error(request, "This requisition has progressed too far to be cancelled by the requester.")
            return redirect("requisition_detail", pk=pr.pk)
            
        try:
            with transaction.atomic():
                pr.status = PurchaseRequisition.STATUS_CANCELLED
                pr.save(update_fields=["status", "updated_at"])
                
                from apps.audit.models import AuditLog
                AuditLog.objects.create(
                    actor=request.user,
                    action=AuditLog.ACTION_UPDATE,
                    target_model="PurchaseRequisition",
                    target_object_id=str(pr.pk),
                    previous_state={"status": pr.status},
                    new_state={"status": PurchaseRequisition.STATUS_CANCELLED},
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
                
            messages.success(request, f"Requisition {pr.pr_number} has been cancelled.")
        except Exception as e:
            messages.error(request, f"Error cancelling requisition: {str(e)}")
            
        return redirect("requisition_detail", pk=pr.pk)
    
    return redirect("requisitions_list")
