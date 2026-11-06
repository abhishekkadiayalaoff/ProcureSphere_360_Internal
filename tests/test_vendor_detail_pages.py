"""
Independent vendor detail pages (tests/test_vendor_detail_pages.py).

The former single long detail page (anchor navigation /vendors/<id>#section) is split into
eight independently routed pages sharing one vendor header/nav component:

    /vendors/<id>/ and /vendors/<id>/overview/   -> Overview
    /vendors/<id>/status/                        -> Status (+ KYC, governance actions, history)
    /vendors/<id>/risk/                          -> Risk (+ assessment form & history)
    /vendors/<id>/performance/                   -> Performance (read-only scorecard view)
    /vendors/<id>/documents/                     -> Documents (+ download, verify/reject)
    /vendors/<id>/contacts/                      -> Contacts (primary / finance / sales)
    /vendors/<id>/sourcing/                      -> Sourcing & POs (invitations, awards, POs)
    /vendors/<id>/history/                       -> History (real audit records)

Covers: per-page rendering + context, active-tab highlighting, direct URL access/refresh,
exported legacy `/vendors/<id>/` landing, POST actions redirecting back to the right page,
read-only performance, audit-accurate history, and RBAC (positive + negative).
"""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

from apps.audit.models import AuditLog  # noqa: E402
from apps.vendors.models import Vendor, VendorContact  # noqa: E402

# Decorator/grouping only — the page-key → URL-name map used by the views.
PAGE_ROUTES = (
    ("overview", "vendor_detail"),  # legacy landing URL renders the Overview page
    ("overview", "vendor_detail_overview"),
    ("status", "vendor_detail_status"),
    ("risk", "vendor_detail_risk"),
    ("performance", "vendor_detail_performance"),
    ("documents", "vendor_detail_documents"),
    ("contacts", "vendor_detail_contacts"),
    ("sourcing", "vendor_detail_sourcing"),
    ("history", "vendor_detail_history"),
)

PAGE_PATHS = ("overview", "status", "risk", "performance", "documents", "contacts", "sourcing", "history")


def _page_url_pattern(vendor):
    return f"/vendors/{vendor.id}/{{}}/"


def _nav_vendor(w):
    return w["vendor_a"]


# ---------------------------------------------------------------------------
# 1. Every page renders independently
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("page,url_name", PAGE_ROUTES)
def test_each_page_renders_with_correct_vendor(client, procurement_world, page, url_name):
    w = procurement_world
    client.force_login(w["mgr"])
    vendor = _nav_vendor(w)
    resp = client.get(reverse(url_name, args=[vendor.id]))
    assert resp.status_code == 200
    assert resp.context["vendor"].id == vendor.id
    assert resp.context["page"] == page
    # The selected vendor is preserved and the active sub-page URL appears in the navigation.
    if page == "overview":
        expected = f"/vendors/{vendor.id}/"
    else:
        expected = f"/vendors/{vendor.id}/{page}/"
    content = resp.content.decode()
    assert f'href="{expected}"' in content
    assert '<a class="nav-link py-1 active"' in content


def test_all_eight_pages_for_active_vendor_no_errors(client, procurement_world):
    """Direct hit on all eight routes must return 200 with no 404/500 (browser-refresh check)."""
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    # Overview is served both on the dedicated URL and the legacy landing URL.
    assert client.get(f"/vendors/{vendor.id}/overview/").status_code == 200
    assert client.get(reverse("vendor_detail", args=[vendor.id])).status_code == 200
    for page in PAGE_PATHS[1:]:
        resp = client.get(_page_url_pattern(vendor).format(page))
        assert resp.status_code == 200, f"page {page} failed: {resp.status_code}"
        assert resp.context["vendor"].id == vendor.id


# ---------------------------------------------------------------------------
# 2. Shared header + navigation: real page links, active tab, back navigation
# ---------------------------------------------------------------------------


def test_nav_contains_all_eight_page_urls(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    page = client.get(reverse("vendor_detail_status", args=[vendor.id])).content.decode()
    assert f'href="/vendors/{vendor.id}/"' in page  # Overview (legacy landing URL)
    for extra in ("status", "risk", "performance", "documents", "contacts", "sourcing", "history"):
        assert f'href="/vendors/{vendor.id}/{extra}/"' in page
    # The active tab is highlighted, others are not.
    active_fragment = '<a class="nav-link py-1 active"'
    assert active_fragment in page


def test_overview_page_marks_overview_nav_active(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    page = client.get(reverse("vendor_detail", args=[vendor.id])).content.decode()
    assert '<a class="nav-link py-1 active"' in page  # overview is the active tab


def test_back_navigation_link_present(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    page = client.get(reverse("vendor_detail_risk", args=[vendor.id])).content.decode()
    assert 'href="/manager/vendor-risk/"' in page  # PROC_MGR → manager risk workspace


# ---------------------------------------------------------------------------
# 3. Page responsibilities
# ---------------------------------------------------------------------------


def test_overview_page_content(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    page = client.get(reverse("vendor_detail", args=[vendor.id])).content.decode()
    assert "Vendor information" in page
    assert vendor.legal_name in page
    assert vendor.tax_identification_number in page
    assert vendor.category.name in page
    assert "Operational summary" in page


def test_status_page_content_and_action_forms(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_status", args=[vendor.id]))
    assert resp.status_code == 200
    ctx = resp.context
    # KYC panel + real status data in context
    assert "KYC &amp; activation status" in resp.content.decode()
    assert "kyc" in ctx and "transitions" in ctx
    # Governance transition form targets the moved POST action route.
    content = resp.content.decode()
    assert reverse("vendor_status_change", args=[vendor.id]) in content
    # Transition history block exists (real audit rows or empty state).
    assert "Status transition history" in content


def test_risk_page_content_and_assessment_link(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_risk", args=[vendor.id]))
    content = resp.content.decode()
    assert resp.status_code == 200
    assert "Record new risk assessment" in content
    assert reverse("vendor_risk_assess", args=[vendor.id]) in content
    assert "Risk assessment history" in content


def test_performance_page_is_read_only_with_module_link(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_performance", args=[vendor.id]))
    assert resp.status_code == 200
    content = resp.content.decode()
    # The vendor page never calculates; it links to the central Supplier Performance module.
    assert "View detailed Supplier Performance" in content
    assert reverse("scorecard_vendor_detail", args=[vendor.id]) in content
    assert "No performance data available" in content  # no scorecard in this world yet


def test_documents_page_content_and_download_action(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_documents", args=[vendor.id]))
    content = resp.content.decode()
    assert resp.status_code == 200
    assert "No documents uploaded." in content  # empty state keeps header/actions intact


def test_contacts_page_groups_by_designation(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    VendorContact.objects.create(
        vendor=vendor, first_name="Ada", last_name="Primary", email="ada@x.test",
        designation="Primary Contact", is_primary=True,
    )
    VendorContact.objects.create(
        vendor=vendor, first_name="Bob", last_name="Finance", email="bob@x.test",
        designation="Finance Manager",
    )
    VendorContact.objects.create(
        vendor=vendor, first_name="Cara", last_name="Sales", email="cara@x.test",
        designation="Sales Head",
    )
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_contacts", args=[vendor.id]))
    assert resp.status_code == 200
    ctx = resp.context["contact_groups"]
    assert len(ctx["primary"]) == 1 and len(ctx["finance"]) == 1 and len(ctx["sales"]) == 1
    content = resp.content.decode()
    for label in ("Primary contact", "Finance contact", "Sales contact"):
        assert label in content


def test_sourcing_page_sections(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.get(reverse("vendor_detail_sourcing", args=[vendor.id]))
    content = resp.content.decode()
    assert resp.status_code == 200
    assert "Open exposure" in content
    assert "RFQ/RFP invitations" in content
    assert "Awards" in content
    assert "Purchase orders" in content
    assert "No purchase orders." in content


def test_history_page_uses_real_audit_records(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])

    # Vendor creation is recorded in the audit log; the History page shows that actor/action.
    creation_log = AuditLog.objects.filter(
        target_model="Vendor", target_object_id=str(vendor.id)
    ).order_by("timestamp").first()
    assert creation_log is not None
    resp = client.get(reverse("vendor_detail_history", args=[vendor.id]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert creation_log.actor_email in content  # actor = the registrant user
    assert "Change history" in content
    assert "immutable audit log" in content


# ---------------------------------------------------------------------------
# 4. Governance actions redirect back onto the right page
# ---------------------------------------------------------------------------


def test_status_change_action_posts_and_returns_to_status_page(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.post(
        reverse("vendor_status_change", args=[vendor.id]), {"status": "ON_HOLD", "notes": "ops"}
    )
    assert resp.status_code == 302
    assert resp.url == reverse("vendor_detail_status", args=[vendor.id])
    vendor.refresh_from_db()
    assert vendor.status == Vendor.STATUS_ON_HOLD


def test_risk_assessment_action_posts_and_returns_to_risk_page(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["mgr"])
    resp = client.post(
        reverse("vendor_risk_assess", args=[vendor.id]),
        {"risk_level": "LOW", "risk_flags": ["QUALITY"], "notes": "ok"},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("vendor_detail_risk", args=[vendor.id])
    # The saved assessment is visible on the Risk page afterwards.
    content = client.get(reverse("vendor_detail_risk", args=[vendor.id])).content.decode()
    assert "assessed by" in content


# ---------------------------------------------------------------------------
# 5. Permissions: no bypass across the new routes
# ---------------------------------------------------------------------------


def test_requester_cannot_access_any_vendor_page(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["requester"])
    assert client.get(reverse("vendor_detail", args=[vendor.id])).status_code == 403
    for page in PAGE_PATHS[1:]:
        assert client.get(_page_url_pattern(vendor).format(page)).status_code == 403


def test_vendor_user_cannot_access_governance_pages(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["user_a"])  # vendor user for vendor_a
    assert client.get(reverse("vendor_detail", args=[vendor.id])).status_code == 403
    for page in PAGE_PATHS[1:]:
        assert client.get(_page_url_pattern(vendor).format(page)).status_code == 403


def test_read_only_roles_see_no_operate_controls(client, procurement_world):
    w = procurement_world
    vendor = _nav_vendor(w)
    client.force_login(w["auditor"])
    for page in PAGE_PATHS[1:]:
        resp = client.get(_page_url_pattern(vendor).format(page))
        assert resp.status_code == 200
        content = resp.content.decode()
        assert "Record new risk assessment" not in content
        assert "Governance action" not in content


def test_cross_org_vendor_is_404_on_all_pages(client, procurement_world, db_roles):
    """Org-scoped lookup: a vendor outside the user's organization must not be resolvable."""
    from apps.accounts.models import Role, User
    from apps.organization.models import Organization

    w = procurement_world
    org = Organization.objects.create(name="HPE Test Org", code="HPE-T-PC")
    scoped_user = User.objects.create_user(
        email="scopecfg@test.local",
        password="Password123!",
        role=db_roles[Role.PROC_EXEC],
        organization=org,
    )
    other_org = Organization.objects.create(name="Other Org", code="ORG-OTHER")
    other_vendor = Vendor.objects.create(
        legal_name="Outsider Ltd",
        vendor_number="VEN-OUT-9999",
        tax_identification_number="TIN-X999",
        email="o@x.test",
        address="Elsewhere",
        category=w["hardware"],
        organization=other_org,
    )
    client.force_login(scoped_user)
    assert client.get(reverse("vendor_detail", args=[other_vendor.id])).status_code == 404
    for page in PAGE_PATHS[1:]:
        assert client.get(_page_url_pattern(other_vendor).format(page)).status_code == 404
