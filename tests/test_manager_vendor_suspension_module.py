import pytest
from django.urls import reverse

from apps.accounts.models import Role, User
from apps.audit.models import AuditLog
from apps.organization.models import CostCenter, Department, Organization
from apps.vendors.models import Vendor, VendorCategory, VendorRiskRecord


@pytest.fixture
def suspension_fixtures(db):
    org = Organization.objects.create(name="Enterprise Global", code="ENT-GLB")
    dept = Department.objects.create(organization=org, name="Procurement Ops", code="PROC-OPS")
    CostCenter.objects.create(
        department=dept, name="Procurement Ops Cost Center", code="CC-PROC"
    )

    manager_role, _ = Role.objects.get_or_create(
        code=Role.PROC_MGR, defaults={"name": "Procurement Manager"}
    )
    requester_role, _ = Role.objects.get_or_create(
        code=Role.REQUESTER, defaults={"name": "Requester"}
    )
    vendor_role, _ = Role.objects.get_or_create(
        code=Role.VENDOR_USER, defaults={"name": "Vendor User"}
    )

    manager_user = User.objects.create_user(
        email="proc_mgr_gov@test.com",
        password="ValidPassword123!",
        role=manager_role,
        organization=org,
        department=dept,
    )
    requester_user = User.objects.create_user(
        email="requester_gov@test.com",
        password="ValidPassword123!",
        role=requester_role,
        organization=org,
        department=dept,
    )
    vendor_user = User.objects.create_user(
        email="vendor_user_gov@test.com",
        password="ValidPassword123!",
        role=vendor_role,
        organization=org,
    )

    cat = VendorCategory.objects.create(name="Cloud Services", code="CAT-CLOUD")
    vendor = Vendor.objects.create(
        legal_name="Apex Technologies Global Inc",
        trade_name="Apex Global",
        vendor_number="VND-2026-9999",
        tax_identification_number="TIN-APEX-9999",
        category=cat,
        organization=org,
        status=Vendor.STATUS_ACTIVE,
        created_by=manager_user,
    )

    VendorRiskRecord.objects.create(
        vendor=vendor,
        risk_level=VendorRiskRecord.RISK_LEVEL_HIGH,
        assessment_notes="High sanctions screening risk triggered.",
        assessed_by=manager_user,
    )

    return {
        "org": org,
        "manager_user": manager_user,
        "requester_user": requester_user,
        "vendor_user": vendor_user,
        "vendor": vendor,
    }


def test_manager_vendor_suspension_view_access_allowed(client, suspension_fixtures):
    """
    Procurement Manager accessing /manager/vendor-risk/suspension/ is seamlessly
    redirected (HTTP 302) to the unified Vendor Risk & Governance desk with the suspension tab active.
    """
    client.force_login(suspension_fixtures["manager_user"])
    url = reverse("manager_vendor_suspension")
    response = client.get(url)

    # 302 Redirect to unified module
    assert response.status_code == 302
    assert "/manager/vendor-risk/" in response.url
    assert "tab=suspension" in response.url

    # Follow redirect
    follow_resp = client.get(url, follow=True)
    assert follow_resp.status_code == 200
    assert "manager/vendor_risk.html" in [t.name for t in follow_resp.templates]
    html = follow_resp.content.decode("utf-8")
    assert "Vendor Risk &amp; Governance Desk" in html
    assert "Sanctions &amp; Suspension Desk" in html
    assert "Live Transaction Exposure" in html
    assert "Apply Governance Action" in html
    assert "Supplier Risk &amp; Governance Directory" in html


def test_manager_vendor_suspension_view_access_denied_for_requester(client, suspension_fixtures):
    """
    Unauthorized roles (e.g. Requester) must receive HTTP 403 Forbidden.
    """
    client.force_login(suspension_fixtures["requester_user"])
    url = reverse("manager_vendor_suspension")
    response = client.get(url)

    assert response.status_code == 403


def test_manager_vendor_suspension_query_params_prefill(client, suspension_fixtures):
    """
    Query parameters ?vendor_id=...&action=SUSPENDED are preserved through the redirect
    and populate the unified desk context.
    """
    vendor = suspension_fixtures["vendor"]
    client.force_login(suspension_fixtures["manager_user"])
    url = f"{reverse('manager_vendor_suspension')}?vendor_id={vendor.id}&action=SUSPENDED"
    response = client.get(url, follow=True)

    assert response.status_code == 200
    assert response.context["target_vendor_id"] == str(vendor.id)
    assert response.context["initial_action"] == "SUSPENDED"
    assert response.context["active_tab"] == "suspension"


def test_manager_unified_vendor_risk_view_tabs(client, suspension_fixtures):
    """
    Unified Vendor Risk & Governance Desk directly renders all three integrated governance tabs:
    Directory, Sanctions & Suspension Desk, and Audit Trail.
    """
    client.force_login(suspension_fixtures["manager_user"])
    url = reverse("manager_vendor_risk")
    response = client.get(url)

    assert response.status_code == 200
    assert "manager/vendor_risk.html" in [t.name for t in response.templates]
    html = response.content.decode("utf-8")
    assert "tab-directory" in html
    assert "tab-suspension" in html
    assert "tab-audit" in html
    assert "Governance Action Formulation" in html
    assert "Comprehensive Governance Audit Ledger" in html


def test_manager_dashboard_view_no_modals_and_has_suspension_desk_link(client, suspension_fixtures):
    """
    Executive dashboard (/manager/):
    - Removed redundant header options (Governance Action modal trigger)
    - Removed modal popup dashboardGovModal
    - Direct links to unified sanctions desk (/manager/vendor-risk/?tab=suspension)
    - High-risk vendor row border styling present
    """
    client.force_login(suspension_fixtures["manager_user"])
    url = reverse("manager_dashboard")
    response = client.get(url)

    assert response.status_code == 200
    html = response.content.decode("utf-8")

    # Assert modal popup is removed
    assert 'id="dashboardGovModal"' not in html
    assert "openDashboardGovModal" not in html

    # Assert direct link to unified suspension module exists
    assert "/manager/vendor-risk/?tab=suspension" in html

    # Assert high-risk border styling pattern exists in script
    assert "border-start border-4 border-danger" in html


def test_governance_action_suspend_and_reinstate_api(client, suspension_fixtures):
    """
    Executing governance action via API updates vendor status and records append-only AuditLog.
    """
    vendor = suspension_fixtures["vendor"]
    manager = suspension_fixtures["manager_user"]
    client.force_login(manager)

    # 1. Suspend the vendor
    suspend_url = f"/api/v1/vendors/{vendor.id}/governance-status/"
    res_suspend = client.post(
        suspend_url,
        data={"status": "SUSPENDED", "reason": "Confirmed OFAC sanctions match."},
        content_type="application/json",
    )
    assert res_suspend.status_code == 200

    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_SUSPENDED
    assert vendor.status_notes == "Confirmed OFAC sanctions match."

    # AuditLog entry created for suspension
    audit_suspend = (
        AuditLog.objects.filter(
            target_model="Vendor",
            target_object_id=str(vendor.id),
        )
        .order_by("-timestamp")
        .first()
    )
    assert audit_suspend is not None
    assert audit_suspend.actor == manager
    assert audit_suspend.action == AuditLog.ACTION_UPDATE
    assert audit_suspend.new_state.get("status") == "SUSPENDED"

    # 2. Reinstate the vendor
    res_reinstate = client.post(
        suspend_url,
        data={"status": "ACTIVE", "reason": "Sanctions screening false-positive resolved."},
        content_type="application/json",
    )
    assert res_reinstate.status_code == 200

    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ACTIVE
    assert vendor.status_notes == "Sanctions screening false-positive resolved."

    audit_reinstate = (
        AuditLog.objects.filter(
            target_model="Vendor",
            target_object_id=str(vendor.id),
        )
        .order_by("-timestamp")
        .first()
    )
    assert audit_reinstate is not None
    assert audit_reinstate.actor == manager
    assert audit_reinstate.action == AuditLog.ACTION_UPDATE
    assert audit_reinstate.new_state.get("status") == "ACTIVE"
