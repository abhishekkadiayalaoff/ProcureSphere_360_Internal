
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
            _ = Department.objects.get(id=department_id)
            _ = CostCenter.objects.get(id=cost_center_id)

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

        except Exception as e:
            messages.error(request, str(e))
            return redirect('requisition_create')

    return render(request, 'pages/requisitions/create.html')

def detail_view(*args, **kwargs): pass
def approve_view(*args, **kwargs): pass
def reject_view(*args, **kwargs): pass
def edit_view(*args, **kwargs): pass
def submit_view(*args, **kwargs): pass
def delete_view(*args, **kwargs): pass
def cancel_view(*args, **kwargs): pass
