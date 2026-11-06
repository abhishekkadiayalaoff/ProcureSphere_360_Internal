import uuid
from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.approvals.models import ApprovalAction
from apps.audit.models import AuditLog
from apps.budgets.models import Budget, BudgetReservation
from apps.organization.models import CostCenter, Department, FiscalPeriod, Organization
from apps.requisitions.models import PurchaseRequisition
from apps.invoices.models import MatchException, SupplierInvoice
from apps.orders.models import PurchaseOrder
from apps.vendors.models import Vendor, VendorCategory


@pytest.fixture
def policy_exception_setup(db):
    org = Organization.objects.create(name="HPE Global", code="HPE")
    other_org = Organization.objects.create(name="Nova Global", code="NOVA")

    dept = Department.objects.create(name="Enterprise Cloud", code="CLOUD", organization=org)
    other_dept = Department.objects.create(name="Nova Cloud", code="N-CLOUD", organization=other_org)

    cost_center = CostCenter.objects.create(code="CC-CLOUD-01", name="Cloud Infra", department=dept)
    other_cc = CostCenter.objects.create(code="CC-NOVA-01", name="Nova Infra", department=other_dept)

    mgr_role, _ = Role.objects.get_or_create(code=Role.PROC_MGR, defaults={"name": "Procurement Manager"})
    req_role, _ = Role.objects.get_or_create(code=Role.REQUESTER, defaults={"name": "Requester"})

    manager_user = User.objects.create_user(
        email="proc_mgr_test@hpe.com",
        password="Password123!",
        role=mgr_role,
        organization=org,
    )
    requester_user = User.objects.create_user(
        email="requester_test@hpe.com",
        password="Password123!",
        role=req_role,
        organization=org,
    )
    other_manager = User.objects.create_user(
        email="proc_mgr_other@nova.com",
        password="Password123!",
        role=mgr_role,
        organization=other_org,
    )

    now = timezone.now().date()
    fiscal_period = FiscalPeriod.objects.create(
        organization=org,
        name="FY2026-Q1",
        year=2026,
        period_number=1,
        start_date=now - timezone.timedelta(days=30),
        end_date=now + timezone.timedelta(days=60),
        is_closed=False,
    )

    budget = Budget.objects.create(
        cost_center=cost_center,
        fiscal_period=fiscal_period,
        allocated_amount=Decimal("50000.00"),
        reserved_amount=Decimal("10000.00"),
        committed_amount=Decimal("10000.00"),
        actual_amount=Decimal("20000.00"),
        allow_overspend=False,
    )

    pr = PurchaseRequisition.objects.create(
        pr_number="PR-2026-EXC-001",
        title="High Performance Storage Expansion",
        justification="Project scale requirement exceeding quarter budget allocation",
        requester=requester_user,
        department=dept,
        cost_center=cost_center,
        status=PurchaseRequisition.STATUS_BUDGET_REVIEW,
        total_amount=Decimal("25000.00"),
        requested_delivery_date=now + timezone.timedelta(days=14),
    )

    # Requisition requested by manager directly (for self-approval testing)
    pr_self = PurchaseRequisition.objects.create(
        pr_number="PR-2026-EXC-002",
        title="Manager Direct Hardware Procurement",
        justification="Executive infrastructure upgrade",
        requester=manager_user,
        department=dept,
        cost_center=cost_center,
        status=PurchaseRequisition.STATUS_BUDGET_REVIEW,
        total_amount=Decimal("15000.00"),
        requested_delivery_date=now + timezone.timedelta(days=14),
    )

    # Cross-org requisition
    pr_other = PurchaseRequisition.objects.create(
        pr_number="PR-2026-NOVA-001",
        title="Nova Infrastructure PR",
        justification="Nova cluster setup",
        requester=other_manager,
        department=other_dept,
        cost_center=other_cc,
        status=PurchaseRequisition.STATUS_BUDGET_REVIEW,
        total_amount=Decimal("30000.00"),
        requested_delivery_date=now + timezone.timedelta(days=14),
    )

    # Vendor and PO and Invoice for Match Exception
    category = VendorCategory.objects.create(name="IT Hardware", code="IT-HW-EXC")
    vendor = Vendor.objects.create(
        legal_name="Apex Storage Systems LLC",
        trade_name="Apex Storage",
        category=category,
        vendor_number="VND-2026-0099",
        status=Vendor.STATUS_ACTIVE,
        organization=org,
    )
    po = PurchaseOrder.objects.create(
        po_number="PO-2026-EXC-001",
        requisition=pr,
        vendor=vendor,
        cost_center=cost_center,
        total_amount=Decimal("20000.00"),
        status=PurchaseOrder.STATUS_ISSUED,
    )
    invoice = SupplierInvoice.objects.create(
        invoice_number="INV-2026-EXC-001",
        po=po,
        vendor=vendor,
        invoice_date=now,
        due_date=now + timezone.timedelta(days=30),
        subtotal=Decimal("23000.00"),
        total_amount=Decimal("23000.00"),
        status=SupplierInvoice.STATUS_EXCEPTION,
    )
    match_exc = MatchException.objects.create(
        invoice=invoice,
        exception_type=MatchException.TYPE_PRICE_VARIANCE,
        variance_amount=Decimal("3000.00"),
        description="Invoice price exceeds PO unit price by 15%",
        status=MatchException.STATUS_OPEN,
    )

    return {
        "org": org,
        "other_org": other_org,
        "manager_user": manager_user,
        "requester_user": requester_user,
        "other_manager": other_manager,
        "budget": budget,
        "pr": pr,
        "pr_self": pr_self,
        "pr_other": pr_other,
        "invoice": invoice,
        "match_exc": match_exc,
    }


@pytest.mark.django_db
def test_manager_policy_exceptions_view_access(client, policy_exception_setup):
    """Procurement Manager can access the policy exceptions view."""
    mgr = policy_exception_setup["manager_user"]
    client.force_login(mgr)
    url = reverse("manager_policy_exceptions")
    res = client.get(url)
    assert res.status_code == 200
    assert "Policy &amp; Budget Exceptions" in res.content.decode() or "Policy Exceptions" in res.content.decode()


@pytest.mark.django_db
def test_policy_exceptions_api_data(client, policy_exception_setup):
    """GET /api/v1/manager/policy-exceptions/ returns calculated KPIs and enriched exception records."""
    mgr = policy_exception_setup["manager_user"]
    client.force_login(mgr)
    url = reverse("manager-policy-exceptions-api")
    res = client.get(url)
    assert res.status_code == 200
    data = res.json()

    assert "kpis" in data
    assert "budget_overrun_prs" in data
    assert "invoice_match_exceptions" in data

    kpis = data["kpis"]
    assert kpis["kpi_overrun_count"] >= 1
    assert kpis["kpi_match_exceptions_count"] >= 1

    overrun_pr = next(p for p in data["budget_overrun_prs"] if p["pr_number"] == "PR-2026-EXC-001")
    assert overrun_pr["pr_number"] == "PR-2026-EXC-001"
    assert overrun_pr["allocated_budget"] == 50000.0
    assert overrun_pr["available_budget"] == 10000.0
    assert overrun_pr["overrun_amount"] == 15000.0

    match_exc = data["invoice_match_exceptions"][0]
    assert match_exc["invoice_number"] == "INV-2026-EXC-001"
    assert match_exc["variance_amount"] == 3000.0


@pytest.mark.django_db
def test_policy_exception_approve_decision(client, policy_exception_setup):
    """Procurement Manager can approve a budget overrun with justification, reserving funds and advancing PR."""
    mgr = policy_exception_setup["manager_user"]
    pr = policy_exception_setup["pr"]
    budget = policy_exception_setup["budget"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "pr_id": str(pr.id),
        "decision": "APPROVE",
        "comments": "Approved by Procurement Manager for critical cloud infrastructure scale.",
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["pr_status"] == PurchaseRequisition.STATUS_SUBMITTED

    # PR should be submitted and reservation created
    pr.refresh_from_db()
    assert pr.status == PurchaseRequisition.STATUS_SUBMITTED

    reservation = BudgetReservation.objects.filter(requisition=pr, status=BudgetReservation.STATUS_RESERVED).first()
    assert reservation is not None
    assert reservation.amount == Decimal("25000.00")

    # AuditLog must be written with OVERRIDE action
    audit = AuditLog.objects.filter(target_model="PurchaseRequisition", target_object_id=str(pr.id), action=AuditLog.ACTION_OVERRIDE).first()
    assert audit is not None
    assert audit.actor == mgr
    assert "critical cloud infrastructure" in audit.new_state.get("comments", "")


@pytest.mark.django_db
def test_policy_exception_reject_decision(client, policy_exception_setup):
    """Procurement Manager can reject a budget overrun with justification, transitioning PR to REJECTED."""
    mgr = policy_exception_setup["manager_user"]
    pr = policy_exception_setup["pr"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "pr_id": str(pr.id),
        "decision": "REJECT",
        "comments": "Rejected due to fiscal quarter budget freeze. Resubmit next quarter.",
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 200
    res_data = res.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["pr_status"] == PurchaseRequisition.STATUS_REJECTED

    pr.refresh_from_db()
    assert pr.status == PurchaseRequisition.STATUS_REJECTED

    # AuditLog must be written with REJECT action
    audit = AuditLog.objects.filter(target_model="PurchaseRequisition", target_object_id=str(pr.id), action=AuditLog.ACTION_REJECT).first()
    assert audit is not None
    assert audit.actor == mgr


@pytest.mark.django_db
def test_policy_exception_self_approval_blocked(client, policy_exception_setup):
    """Separation of duties: A Procurement Manager cannot approve their own requisition budget overrun."""
    mgr = policy_exception_setup["manager_user"]
    pr_self = policy_exception_setup["pr_self"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "pr_id": str(pr_self.id),
        "decision": "APPROVE",
        "comments": "Attempting self-approval of own hardware PR.",
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "SEPARATION_OF_DUTIES_VIOLATION"
    assert "cannot approve a budget" in str(data).lower()


@pytest.mark.django_db
def test_policy_exception_missing_comments_blocked(client, policy_exception_setup):
    """Mandatory audit comments: Decisions without sufficient justification are rejected."""
    mgr = policy_exception_setup["manager_user"]
    pr = policy_exception_setup["pr"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "pr_id": str(pr.id),
        "decision": "APPROVE",
        "comments": "OK",  # Too short (< 5 chars)
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 400
    data = res.json()
    assert data["code"] == "JUSTIFICATION_REQUIRED"


@pytest.mark.django_db
def test_policy_exception_cross_org_blocked(client, policy_exception_setup):
    """Tenant isolation: Procurement Manager cannot override budget overrun of a different organization."""
    mgr = policy_exception_setup["manager_user"]
    pr_other = policy_exception_setup["pr_other"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "pr_id": str(pr_other.id),
        "decision": "APPROVE",
        "comments": "Cross-organization approval attempt.",
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 403
    data = res.json()
    assert "forbidden" in str(data).lower() or "organization" in str(data).lower()


@pytest.mark.django_db
def test_invoice_match_exception_resolution_blocked_for_manager(client, policy_exception_setup):
    """Authority boundary enforcement: Procurement Manager cannot resolve/override invoice match exceptions."""
    mgr = policy_exception_setup["manager_user"]
    client.force_login(mgr)

    decision_url = reverse("manager-budget-exception-decision-api")
    payload = {
        "exception_type": "INVOICE_MATCH",
        "match_exception_id": str(policy_exception_setup["match_exc"].id),
        "decision": "RESOLVE",
        "comments": "Procurement Manager attempting to resolve finance invoice match exception.",
    }
    res = client.post(decision_url, data=payload, content_type="application/json")
    assert res.status_code == 403
    data = res.json()
    assert data["code"] == "AUTHORITY_BOUNDARY_VIOLATION"
    assert "finance" in str(data).lower()
