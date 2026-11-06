import csv
import io
import json
import uuid
from decimal import Decimal
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.audit.selectors import (
    get_audit_logs,
    get_audit_metrics,
    get_auditor_dashboard_data,
    get_entity_audit_trail,
    get_vendor_compliance_audit,
    get_approval_history_audit,
    get_sourcing_activity_audit,
    get_po_changes_audit,
    get_invoice_exceptions_audit,
    get_contract_changes_audit,
    get_security_events_audit,
)
from apps.audit.services import (
    create_audit_log_service,
    export_auditor_data_service,
    get_transaction_lifecycle_service,
)
from apps.contracts.models import Contract
from apps.invoices.models import MatchException, SupplierInvoice
from apps.orders.models import POLine, PurchaseOrder
from apps.organization.models import CostCenter, Department, FiscalPeriod, Organization
from apps.requisitions.models import PurchaseRequisition
from apps.sourcing.models import SourcingEvent
from apps.vendors.models import Vendor, VendorCategory


@pytest.fixture
def multi_org_audit_setup(db):
    org_a = Organization.objects.create(name="HPE Global", code="HPE")
    org_b = Organization.objects.create(name="Acme Corp", code="ACME")

    dept_a = Department.objects.create(name="IT Services", code="IT", organization=org_a)
    dept_b = Department.objects.create(name="Finance Ops", code="FIN", organization=org_b)

    cc_a = CostCenter.objects.create(code="CC-IT-01", name="IT Infra", department=dept_a)
    cc_b = CostCenter.objects.create(code="CC-FIN-01", name="Finance Infra", department=dept_b)

    role_auditor, _ = Role.objects.get_or_create(code=Role.AUDITOR, defaults={"name": "Auditor"})
    role_super, _ = Role.objects.get_or_create(code=Role.SUPER_ADMIN, defaults={"name": "Super Admin"})
    role_mgr, _ = Role.objects.get_or_create(code=Role.PROC_MGR, defaults={"name": "Procurement Manager"})
    role_req, _ = Role.objects.get_or_create(code=Role.REQUESTER, defaults={"name": "Requester"})
    role_finance, _ = Role.objects.get_or_create(code=Role.FINANCE_AP, defaults={"name": "Finance AP"})
    role_vendor, _ = Role.objects.get_or_create(code=Role.VENDOR_USER, defaults={"name": "Vendor"})
    role_stores, _ = Role.objects.get_or_create(code=Role.STORES_RECEIVER, defaults={"name": "Stores Receiver"})

    auditor_a = User.objects.create_user(
        email="auditor.a@hpe.com",
        password="Password123!",
        role=role_auditor,
        organization=org_a,
    )
    auditor_b = User.objects.create_user(
        email="auditor.b@acme.com",
        password="Password123!",
        role=role_auditor,
        organization=org_b,
    )
    super_admin = User.objects.create_superuser(
        email="admin@global.com",
        password="Password123!",
        role=role_super,
        organization=org_a,
    )
    manager_a = User.objects.create_user(
        email="mgr.a@hpe.com",
        password="Password123!",
        role=role_mgr,
        organization=org_a,
    )
    finance_a = User.objects.create_user(
        email="finance.a@hpe.com",
        password="Password123!",
        role=role_finance,
        organization=org_a,
    )
    requester_a = User.objects.create_user(
        email="req.a@hpe.com",
        password="Password123!",
        role=role_req,
        organization=org_a,
    )
    vendor_user = User.objects.create_user(
        email="vendor.rep@supplier.com",
        password="Password123!",
        role=role_vendor,
        organization=org_a,
    )
    stores_user = User.objects.create_user(
        email="stores.a@hpe.com",
        password="Password123!",
        role=role_stores,
        organization=org_a,
    )

    cat_a = VendorCategory.objects.create(name="Cloud Services", code="CAT-CLOUD")
    cat_b = VendorCategory.objects.create(name="Office Supplies", code="CAT-OFFICE")

    vendor_a = Vendor.objects.create(
        legal_name="Cloud Solutions Inc",
        trade_name="Cloud Solutions",
        category=cat_a,
        organization=org_a,
        tax_identification_number="TIN-CLOUD-01",
        vendor_number="VND-CLOUD-01",
        status=Vendor.STATUS_ACTIVE,
        is_event_eligible=True,
    )
    vendor_b = Vendor.objects.create(
        legal_name="Paper Supplies Ltd",
        trade_name="Paper Supplies",
        category=cat_b,
        organization=org_b,
        tax_identification_number="TIN-PAPER-02",
        vendor_number="VND-PAPER-02",
        status=Vendor.STATUS_SUSPENDED,
        is_event_eligible=False,
    )

    today = timezone.now().date()
    pr_a = PurchaseRequisition.objects.create(
        pr_number="PR-HPE-2026-0001",
        department=dept_a,
        cost_center=cc_a,
        requester=requester_a,
        title="Server Purchase",
        total_amount=Decimal("15000.00"),
        status=PurchaseRequisition.STATUS_SUBMITTED,
        requested_delivery_date=today + timezone.timedelta(days=14),
    )
    pr_b = PurchaseRequisition.objects.create(
        pr_number="PR-ACME-2026-0001",
        department=dept_b,
        cost_center=cc_b,
        requester=auditor_b,
        title="Paper Batch",
        total_amount=Decimal("5000.00"),
        status=PurchaseRequisition.STATUS_SUBMITTED,
        requested_delivery_date=today + timezone.timedelta(days=14),
    )

    po_a = PurchaseOrder.objects.create(
        po_number="PO-HPE-2026-0001",
        requisition=pr_a,
        vendor=vendor_a,
        cost_center=cc_a,
        total_amount=Decimal("15000.00"),
        status=PurchaseOrder.STATUS_ISSUED,
    )
    po_b = PurchaseOrder.objects.create(
        po_number="PO-ACME-2026-0001",
        requisition=pr_b,
        vendor=vendor_b,
        cost_center=cc_b,
        total_amount=Decimal("5000.00"),
        status=PurchaseOrder.STATUS_ISSUED,
    )

    today = timezone.now().date()
    inv_a = SupplierInvoice.objects.create(
        invoice_number="INV-HPE-001",
        vendor=vendor_a,
        po=po_a,
        invoice_date=today,
        due_date=today + timezone.timedelta(days=30),
        subtotal=Decimal("15500.00"),
        total_amount=Decimal("15500.00"),
        status=SupplierInvoice.STATUS_EXCEPTION,
    )
    inv_b = SupplierInvoice.objects.create(
        invoice_number="INV-ACME-001",
        vendor=vendor_b,
        po=po_b,
        invoice_date=today,
        due_date=today + timezone.timedelta(days=30),
        subtotal=Decimal("5200.00"),
        total_amount=Decimal("5200.00"),
        status=SupplierInvoice.STATUS_EXCEPTION,
    )

    # Create Audit Logs for org_a
    log_a1 = AuditLog.objects.create(
        actor=auditor_a,
        action=AuditLog.ACTION_CREATE,
        target_model="PurchaseRequisition",
        target_object_id=str(pr_a.id),
        previous_state={},
        new_state={"status": PurchaseRequisition.STATUS_SUBMITTED},
        ip_address="127.0.0.1",
    )
    log_a2 = AuditLog.objects.create(
        actor=manager_a,
        action=AuditLog.ACTION_APPROVE,
        target_model="PurchaseOrder",
        target_object_id=str(po_a.id),
        previous_state={"status": PurchaseOrder.STATUS_DRAFT},
        new_state={"status": PurchaseOrder.STATUS_ISSUED},
        ip_address="127.0.0.1",
    )

    # Create Audit Logs for org_b
    log_b1 = AuditLog.objects.create(
        actor=auditor_b,
        action=AuditLog.ACTION_CREATE,
        target_model="PurchaseRequisition",
        target_object_id=str(pr_b.id),
        previous_state={},
        new_state={"status": PurchaseRequisition.STATUS_SUBMITTED},
        ip_address="10.0.0.1",
    )
    log_b2 = AuditLog.objects.create(
        actor=auditor_b,
        action=AuditLog.ACTION_UPDATE,
        target_model="Vendor",
        target_object_id=str(vendor_b.id),
        previous_state={"status": Vendor.STATUS_ACTIVE},
        new_state={"status": Vendor.STATUS_SUSPENDED},
        ip_address="10.0.0.1",
    )

    return {
        "org_a": org_a,
        "org_b": org_b,
        "auditor_a": auditor_a,
        "auditor_b": auditor_b,
        "super_admin": super_admin,
        "manager_a": manager_a,
        "finance_a": finance_a,
        "requester_a": requester_a,
        "vendor_user": vendor_user,
        "stores_user": stores_user,
        "pr_a": pr_a,
        "pr_b": pr_b,
        "po_a": po_a,
        "po_b": po_b,
        "inv_a": inv_a,
        "inv_b": inv_b,
        "vendor_a": vendor_a,
        "vendor_b": vendor_b,
        "log_a1": log_a1,
        "log_a2": log_a2,
        "log_b1": log_b1,
        "log_b2": log_b2,
    }


@pytest.mark.django_db
class TestAuditorRoleAccessEnforcement:
    """Verify that only Auditor and Super Admin can access auditor views and APIs."""

    def test_auditor_access_allowed(self, client, multi_org_audit_setup):
        auditor = multi_org_audit_setup["auditor_a"]
        client.force_login(auditor)

        res = client.get(reverse("auditor_dashboard"))
        assert res.status_code == 200

        res_logs = client.get(reverse("auditor_logs"))
        assert res_logs.status_code == 200

    def test_super_admin_access_allowed(self, client, multi_org_audit_setup):
        admin = multi_org_audit_setup["super_admin"]
        client.force_login(admin)

        res = client.get(reverse("auditor_dashboard"))
        assert res.status_code == 200

    @pytest.mark.parametrize("role_key", [
        "finance_a",
        "manager_a",
        "requester_a",
        "vendor_user",
        "stores_user",
    ])
    def test_unauthorized_roles_denied_dashboard_access(self, client, multi_org_audit_setup, role_key):
        user = multi_org_audit_setup[role_key]
        client.force_login(user)

        res = client.get(reverse("auditor_dashboard"))
        assert res.status_code == 403

        res_logs = client.get(reverse("auditor_logs"))
        assert res_logs.status_code == 403

        res_api = client.get(reverse("audit_metrics"))
        assert res_api.status_code == 403


@pytest.mark.django_db
class TestAuditorOrganizationDataIsolation:
    """Verify that an Auditor can only inspect and query records for their authorized organization."""

    def test_auditor_logs_selector_scoped_to_organization(self, multi_org_audit_setup):
        org_a = multi_org_audit_setup["org_a"]
        org_b = multi_org_audit_setup["org_b"]

        logs_a = get_audit_logs(organization=org_a)
        assert logs_a["total_count"] == 2
        assert all(str(log.target_object_id) in [str(multi_org_audit_setup["pr_a"].id), str(multi_org_audit_setup["po_a"].id)] for log in logs_a["logs"])

        logs_b = get_audit_logs(organization=org_b)
        assert logs_b["total_count"] == 2
        assert all(str(log.target_object_id) in [str(multi_org_audit_setup["pr_b"].id), str(multi_org_audit_setup["vendor_b"].id)] for log in logs_b["logs"])

    def test_auditor_cannot_see_other_org_logs_via_api(self, client, multi_org_audit_setup):
        auditor_a = multi_org_audit_setup["auditor_a"]
        client.force_login(auditor_a)

        # GET audit logs API
        res = client.get("/api/v1/audit/logs/")
        assert res.status_code == 200
        data = res.json()
        results = data.get("results", data)
        target_ids = [r["target_object_id"] for r in results]

        # Auditor A should see org_a targets
        assert str(multi_org_audit_setup["pr_a"].id) in target_ids
        # Auditor A should NEVER see org_b targets
        assert str(multi_org_audit_setup["pr_b"].id) not in target_ids
        assert str(multi_org_audit_setup["vendor_b"].id) not in target_ids

    def test_auditor_cross_organization_lifecycle_denied(self, client, multi_org_audit_setup):
        auditor_a = multi_org_audit_setup["auditor_a"]
        client.force_login(auditor_a)

        # Auditor A queries own PR lifecycle -> OK
        res_own = client.get(
            f"/api/v1/audit/logs/lifecycle/?entity_type=PurchaseRequisition&identifier={multi_org_audit_setup['pr_a'].id}"
        )
        assert res_own.status_code == 200

        # Auditor A attempts cross-org access to Acme Corp PR lifecycle -> 403 Forbidden
        res_cross = client.get(
            f"/api/v1/audit/logs/lifecycle/?entity_type=PurchaseRequisition&identifier={multi_org_audit_setup['pr_b'].id}"
        )
        assert res_cross.status_code == 403
        assert "access to cross-organization" in res_cross.json().get("error", {}).get("message", "").lower() or "forbidden" in str(res_cross.json()).lower()

    def test_auditor_cross_organization_entity_trail_denied(self, client, multi_org_audit_setup):
        auditor_a = multi_org_audit_setup["auditor_a"]
        client.force_login(auditor_a)

        # Cross-org entity trail -> 403 Forbidden
        res = client.get(
            f"/api/v1/audit/logs/entity-trail/?target_model=Vendor&target_object_id={multi_org_audit_setup['vendor_b'].id}"
        )
        assert res.status_code == 403

    def test_auditor_export_scoped_to_organization(self, multi_org_audit_setup):
        auditor_a = multi_org_audit_setup["auditor_a"]
        res = export_auditor_data_service(
            export_type="vendor_compliance",
            export_format="csv",
            actor=auditor_a,
        )
        content = res["content"]
        # Must contain vendor A but not vendor B
        assert "Cloud Solutions" in content
        assert "Paper Supplies" not in content

    def test_auditor_metrics_scoped_to_organization(self, multi_org_audit_setup):
        org_a = multi_org_audit_setup["org_a"]
        metrics_a = get_audit_metrics(organization=org_a)
        assert metrics_a["total_logs_all_time"] == 2

        org_b = multi_org_audit_setup["org_b"]
        metrics_b = get_audit_metrics(organization=org_b)
        assert metrics_b["total_logs_all_time"] == 2
