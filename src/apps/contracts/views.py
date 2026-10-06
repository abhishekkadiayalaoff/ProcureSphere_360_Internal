from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.models import Role
from apps.audit.models import AuditLog

from .forms import (
    ContractAmendmentForm,
    ContractCreateForm,
    ContractDocumentForm,
    ContractMilestoneForm,
    ContractObligationForm,
    ContractRenewalForm,
)
from .models import Contract, ContractMilestone, ContractObligation
from .selectors import (
    get_contract_by_id,
    get_contracts_qs,
    get_legal_dashboard_metrics,
)
from .services import (
    add_contract_milestone_service,
    add_contract_obligation_service,
    approve_business_service,
    approve_legal_review_service,
    complete_contract_milestone_service,
    create_contract_service,
    create_contract_version_service,
    fulfill_contract_obligation_service,
    reject_legal_review_service,
    renew_contract_service,
    submit_for_legal_review_service,
    terminate_contract_service,
    upload_contract_document_service,
)


@login_required(login_url="/login/")
def list_view(request):
    """
    Contract Register List View with filtering by status, search query, and metrics.
    """
    status_filter = request.GET.get("status", "").strip()
    search_query = request.GET.get("q", "").strip()

    items = get_contracts_qs(user=request.user, status=status_filter, search=search_query)
    metrics = get_legal_dashboard_metrics()

    context = {
        "items": items,
        "metrics": metrics,
        "current_status": status_filter,
        "search_query": search_query,
        "statuses": Contract.STATUS_CHOICES,
    }
    return render(request, "pages/contracts/list.html", context)


@login_required(login_url="/login/")
def create_view(request):
    """
    Creates a new Contract in DRAFT state.
    """
    role_code = getattr(request.user, "role_code", None) or (
        request.user.role.code if getattr(request.user, "role", None) else None
    )
    if role_code == Role.AUDITOR:
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot draft contracts.",
        )
        return redirect("contracts_list")

    if request.method == "POST":
        form = ContractCreateForm(request.POST)
        if form.is_valid():
            try:
                contract = create_contract_service(
                    title=form.cleaned_data["title"],
                    vendor=form.cleaned_data["vendor"],
                    contract_value=form.cleaned_data["contract_value"],
                    start_date=form.cleaned_data["start_date"],
                    end_date=form.cleaned_data["end_date"],
                    renewal_notice_days=form.cleaned_data["renewal_notice_days"],
                    sourcing_event=form.cleaned_data.get("sourcing_event"),
                    po=form.cleaned_data.get("po"),
                    contract_owner=request.user,
                )
                messages.success(
                    request, f"Contract '{contract.contract_number}' drafted successfully."
                )
                return redirect("contract_detail", contract_id=contract.id)
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Failed to create contract: {str(e)}")
    else:
        form = ContractCreateForm()

    return render(request, "pages/contracts/create.html", {"form": form})


@login_required(login_url="/login/")
def detail_view(request, contract_id):
    """
    Contract Lifecycle & SLA Workspace Detail View.
    """
    contract = get_contract_by_id(contract_id)
    if not contract:
        messages.error(request, "Contract record not found.")
        return redirect("contracts_list")

    audit_logs = AuditLog.objects.filter(
        target_model="Contract", target_object_id=str(contract.id)
    ).order_by("-timestamp")

    amendment_form = ContractAmendmentForm(
        initial={
            "contract_value": contract.contract_value,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
        }
    )
    milestone_form = ContractMilestoneForm()
    obligation_form = ContractObligationForm()
    document_form = ContractDocumentForm()
    renewal_form = ContractRenewalForm(initial={"new_value": contract.contract_value})

    role_code = getattr(request.user, "role_code", None) or (
        request.user.role.code if getattr(request.user, "role", None) else None
    )
    is_legal_mgr = role_code in [Role.LEGAL_MGR, Role.SUPER_ADMIN]
    is_proc_mgr = role_code in [Role.PROC_MGR, Role.SUPER_ADMIN]

    context = {
        "contract": contract,
        "versions": contract.versions.all().order_by("-version_number"),
        "milestones": contract.milestones.all().order_by("due_date"),
        "obligations": contract.obligations.all().order_by("due_date"),
        "documents": contract.documents.all().order_by("-created_at"),
        "alerts": contract.alerts.all().order_by("-triggered_at"),
        "audit_logs": audit_logs,
        "amendment_form": amendment_form,
        "milestone_form": milestone_form,
        "obligation_form": obligation_form,
        "document_form": document_form,
        "renewal_form": renewal_form,
        "is_legal_mgr": is_legal_mgr,
        "is_proc_mgr": is_proc_mgr,
    }
    return render(request, "pages/contracts/detail.html", context)


def _is_auditor(user):
    role_code = getattr(user, "role_code", None) or (
        user.role.code if getattr(user, "role", None) else None
    )
    return role_code == Role.AUDITOR


@login_required(login_url="/login/")
@require_POST
def submit_legal_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    if _is_auditor(request.user):
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot modify contracts.",
        )
        return redirect("contract_detail", contract_id=contract.id)
    notes = request.POST.get("notes", "")
    try:
        submit_for_legal_review_service(contract=contract, user=request.user, notes=notes)
        messages.success(
            request, f"Contract '{contract.contract_number}' submitted for Legal Review."
        )
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def legal_approve_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    if _is_auditor(request.user):
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot approve contracts.",
        )
        return redirect("contract_detail", contract_id=contract.id)
    notes = request.POST.get("notes", "")
    try:
        approve_legal_review_service(contract=contract, user=request.user, notes=notes)
        messages.success(
            request,
            f"Contract '{contract.contract_number}' Legal Review APPROVED. Status moved to Business Approval.",
        )
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def legal_reject_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    if _is_auditor(request.user):
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot reject contracts.",
        )
        return redirect("contract_detail", contract_id=contract.id)
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Rejection reason is required.")
        return redirect("contract_detail", contract_id=contract.id)
    try:
        reject_legal_review_service(contract=contract, user=request.user, reason=reason)
        messages.warning(
            request,
            f"Contract '{contract.contract_number}' Legal Review REJECTED and returned to Draft.",
        )
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def business_approve_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    if _is_auditor(request.user):
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot approve contracts.",
        )
        return redirect("contract_detail", contract_id=contract.id)
    notes = request.POST.get("notes", "")
    try:
        approve_business_service(contract=contract, user=request.user, notes=notes)
        messages.success(
            request,
            f"Contract '{contract.contract_number}' Business Approval completed! Contract is now ACTIVE.",
        )
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def amend_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    if _is_auditor(request.user):
        messages.error(
            request,
            "Permission Denied: Compliance Auditors hold strictly read-only permissions and cannot amend contracts.",
        )
        return redirect("contract_detail", contract_id=contract.id)
    form = ContractAmendmentForm(request.POST)
    if form.is_valid():
        try:
            version_record = create_contract_version_service(
                contract=contract,
                user=request.user,
                amendment_summary=form.cleaned_data["amendment_summary"],
                contract_value=form.cleaned_data["contract_value"],
                start_date=form.cleaned_data["start_date"],
                end_date=form.cleaned_data["end_date"],
            )
            messages.success(
                request,
                f"Contract '{contract.contract_number}' amended to Version {version_record.version_number}.",
            )
        except ValidationError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Invalid amendment form details.")
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def milestone_create_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    form = ContractMilestoneForm(request.POST)
    if form.is_valid():
        add_contract_milestone_service(
            contract=contract,
            title=form.cleaned_data["title"],
            due_date=form.cleaned_data["due_date"],
            amount=form.cleaned_data["amount"],
        )
        messages.success(request, f"Milestone '{form.cleaned_data['title']}' added successfully.")
    else:
        messages.error(request, "Invalid milestone details.")
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def milestone_toggle_view(request, contract_id, milestone_id):
    milestone = get_object_or_404(ContractMilestone, id=milestone_id, contract_id=contract_id)
    complete_contract_milestone_service(milestone=milestone, user=request.user)
    messages.success(request, f"Milestone '{milestone.title}' marked as COMPLETED.")
    return redirect("contract_detail", contract_id=contract_id)


@login_required(login_url="/login/")
@require_POST
def obligation_create_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    form = ContractObligationForm(request.POST)
    if form.is_valid():
        add_contract_obligation_service(
            contract=contract,
            title=form.cleaned_data["title"],
            responsible_party=form.cleaned_data["responsible_party"],
            due_date=form.cleaned_data["due_date"],
        )
        messages.success(request, f"Obligation '{form.cleaned_data['title']}' added successfully.")
    else:
        messages.error(request, "Invalid obligation details.")
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def obligation_toggle_view(request, contract_id, obligation_id):
    obligation = get_object_or_404(ContractObligation, id=obligation_id, contract_id=contract_id)
    fulfill_contract_obligation_service(obligation=obligation, user=request.user)
    messages.success(request, f"Obligation '{obligation.title}' marked as FULFILLED.")
    return redirect("contract_detail", contract_id=contract_id)


@login_required(login_url="/login/")
@require_POST
def document_upload_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    form = ContractDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        upload_contract_document_service(
            contract=contract,
            user=request.user,
            title=form.cleaned_data["title"],
            file=form.cleaned_data["file"],
        )
        messages.success(request, f"Document '{form.cleaned_data['title']}' uploaded successfully.")
    else:
        messages.error(request, "Invalid file upload submission.")
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def renew_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    form = ContractRenewalForm(request.POST)
    if form.is_valid():
        try:
            renew_contract_service(
                contract=contract,
                user=request.user,
                new_end_date=form.cleaned_data["new_end_date"],
                new_value=form.cleaned_data.get("new_value"),
                notes=form.cleaned_data.get("notes", ""),
            )
            messages.success(
                request, f"Contract '{contract.contract_number}' successfully RENEWED."
            )
        except ValidationError as e:
            messages.error(request, str(e))
    else:
        messages.error(request, "Invalid renewal date or details.")
    return redirect("contract_detail", contract_id=contract.id)


@login_required(login_url="/login/")
@require_POST
def terminate_view(request, contract_id):
    contract = get_object_or_404(Contract, id=contract_id)
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Termination reason is required.")
        return redirect("contract_detail", contract_id=contract.id)
    try:
        terminate_contract_service(contract=contract, user=request.user, reason=reason)
        messages.warning(request, f"Contract '{contract.contract_number}' TERMINATED.")
    except ValidationError as e:
        messages.error(request, str(e))
    return redirect("contract_detail", contract_id=contract.id)
