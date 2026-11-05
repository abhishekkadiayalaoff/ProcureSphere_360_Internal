"""
Supplier Performance module separation tests.

Scorecards are the single source of truth for supplier performance calcuations; Vendor
Master/Governance are read-only consumers; SLA is reported in a dedicated section with
per-contract history; ON_HOLD vendors are blocked from new sourcing activity.

Covers: regressions, calculation confidence, SLA section, cross-module sync, RBAC,
duplicate-prevention, hold/reactivation blocking, historical preservation and the
scorecards REST API.
"""

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

from apps.audit.models import AuditLog  # noqa: E402
from apps.contracts.models import Contract, ContractObligation  # noqa: E402
from apps.scorecards.models import (  # noqa: E402
    VendorScorecard,
    VendorScorecardSLAMetric,
)
from apps.scorecards.permissions import SCORECARD_CALCULATE_ROLES  # noqa: E402
from apps.sourcing import services as sourcing_svc  # noqa: E402
from apps.sourcing.models import SourcingEvent  # noqa: E402
from apps.vendors.models import Vendor, VendorRiskRecord  # noqa: E402
from apps.vendors.services import set_vendor_status_governance_service  # noqa: E402


def _invite_and_publish(w, title):
    event = sourcing_svc.create_sourcing_event_service(
        title=title,
        event_type="RFQ",
        bid_start_date=timezone.now(),
        bid_end_date=timezone.now() + timedelta(days=1),
        description="x",
        created_by_user=w["exec"],
    )
    sourcing_svc.invite_vendors_to_event_service(
        event=event, vendor_ids=[w["vendor_a"].id], invited_by=w["exec"]
    )
    sourcing_svc.publish_sourcing_event_service(event=event, user=w["exec"])
    return event


def _bid():
    return [{"item_description": "Item", "quantity": 1, "quoted_unit_price": 10}]


# --------------------------------------------------------------------------
# 1. Regressions: Vendor Master detail is read-only about performance
# --------------------------------------------------------------------------


class TestVendorMasterRegression:
    def test_detail_page_has_no_calculate_form_and_links_scorecard_app(
        self, client, procurement_world
    ):
        w = procurement_world
        client.force_login(w["exec"])
        res = client.get(f"/vendors/{w['vendor_a'].id}/")
        assert res.status_code == 200
        body = res.content.decode()
        assert "Calculate scorecard" not in body
        assert "scorecard_calculate" not in body
        # No scorecard yet → empty state, no link
        assert "No performance data available." in body
        # After a scorecard exists the page is read-only and links to the scorecards app
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        res = client.get(f"/vendors/{w['vendor_a'].id}/")
        assert res.status_code == 200
        body = res.content.decode()
        assert "View detailed Supplier Performance" in body
        assert "Calculate scorecard" not in body

    def test_detail_page_keeps_no_data_empty_state(self, client, procurement_world):
        w = procurement_world
        client.force_login(w["exec"])
        res = client.get(f"/vendors/{w['vendor_draft'].id}/")
        assert res.status_code == 200
        assert "No performance data available." in res.content.decode()

    def test_governance_register_hides_registration_actions(
        self, client, procurement_world
    ):
        w = procurement_world
        client.force_login(w["exec"])
        governance = client.get("/vendors/governance/").content.decode()
        assert "Register Vendor" not in governance
        assert "Import Vendors" not in governance
        master = client.get("/vendors/").content.decode()
        assert "Register Vendor" in master

    def test_vendor_without_scorecard_has_none_in_detail_context(
        self, client, procurement_world
    ):
        w = procurement_world
        client.force_login(w["exec"])
        res = client.get(f"/vendors/{w['vendor_a'].id}/")
        assert res.context["latest_scorecard"] is None
        assert "scorecards" not in res.context  # heavy trend list removed


# --------------------------------------------------------------------------
# 2. Calculation confidence: only the scorecards service writes scorecards
# --------------------------------------------------------------------------


class TestCalculation:
    def test_calculate_service_persizes_no_data_norms(self, procurement_world):
        w = procurement_world
        card = VendorScorecard.objects.create(
            vendor=w["vendor_a"],
            evaluation_period="Q4-2026",
            evaluated_by=w["exec"],
            delivery_score=None,
            quality_score=None,
            price_score=None,
            compliance_score=100,
        )
        assert card.composite_score == 100  # re-normalised over indicators with data only

    def test_ui_calculation_still_works_in_supplier_performance(self, client, procurement_world):
        w = procurement_world
        client.force_login(w["exec"])
        res = client.post(
            "/scorecards/calculate/",
            {"vendor_id": str(w["vendor_a"].id), "period": "Q4-2026"},
        )
        assert res.status_code == 302
        assert VendorScorecard.objects.filter(vendor=w["vendor_a"]).count() == 1
        assert AuditLog.objects.filter(target_model="VendorScorecard").exists()

    def test_vendor_page_show_rw_calculated_scorecard_after_calculate(
        self, client, procurement_world
    ):
        w = procurement_world
        card = VendorScorecard(
            vendor=w["vendor_a"],
            evaluation_period="Q4-2026",
            evaluated_by=w["exec"],
            compliance_score=100,
        )
        card.save()
        client.force_login(w["manager"] if "manager" in w else w["exec"])
        res = client.get(f"/vendors/{w['vendor_a'].id}/")
        assert res.status_code == 200
        assert res.context["latest_scorecard"].composite_score == 100

    def test_calculate_roles_helpers(self, procurement_world):
        w = procurement_world
        from apps.scorecards.permissions import can_calculate_scorecards

        assert can_calculate_scorecards(w["exec"])
        assert can_calculate_scorecards(w["mgr"])
        assert not can_calculate_scorecards(w["auditor"])
        assert not can_calculate_scorecards(w["requester"])


# --------------------------------------------------------------------------
# 3. SLA section: dedicated scorecard page, per-contract snapshots, history
# --------------------------------------------------------------------------


def _make_contract_with_obligations(w):
    contract = Contract.objects.create(
        contract_number="CON-SLA-1",
        title="SLA contract",
        vendor=w["vendor_a"],
        status=Contract.STATUS_ACTIVE,
        start_date=timezone.localdate() - timedelta(days=30),
        end_date=timezone.localdate() + timedelta(days=180),
        contract_owner=w["mgr"],
    )
    today = timezone.localdate()
    # 3 due vendor obligations: 2 met on time, 1 unfulfilled (breached)
    ContractObligation.objects.create(
        contract=contract,
        title="Deliver audit pack",
        responsible_party="VENDOR",
        due_date=today - timedelta(days=10),
        is_fulfilled=True,
        fulfilled_at=timezone.now() - timedelta(days=12),
    )
    ContractObligation.objects.create(
        contract=contract,
        title="Quarterly report",
        responsible_party="VENDOR",
        due_date=today - timedelta(days=5),
        is_fulfilled=True,
        fulfilled_at=timezone.now() - timedelta(days=6),  # on/before the due date
    )
    ContractObligation.objects.create(
        contract=contract,
        title="Renew certification",
        responsible_party="VENDOR",
        due_date=today - timedelta(days=2),
        is_fulfilled=False,
    )
    return contract


class TestSlaSection:
    def test_compute_sla_and_snapshot_rows(self, procurement_world):
        w = procurement_world
        contract = _make_contract_with_obligations(w)
        from apps.scorecards.services import calculate_vendor_scorecard_service

        card = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"],
            evaluation_period="Q5-2026",
            evaluated_by_user=w["exec"],
        )
        # 2 of 3 due obligations met on time
        assert float(card.sla_score) == pytest.approx(2 / 3 * 100, abs=0.01)
        rows = VendorScorecardSLAMetric.objects.filter(scorecard=card)
        assert rows.filter(metric_code="OVERALL").count() == 1
        contract_rows = rows.filter(metric_code="CONTRACT")
        assert contract_rows.count() == 1
        assert contract_rows.first().contract_id == contract.id
        overall = rows.get(metric_code="OVERALL")
        assert overall.breaches == 1
        assert overall.observations == 3
        assert rows.filter(actual_pct=None).count() == 0

    def test_sla_no_data_when_no_due_obligations(self, procurement_world):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        card = calculate_vendor_scorecard_service(
            vendor=w["vendor_b"],
            evaluation_period="Q5-2026",
            evaluated_by_user=w["exec"],
        )
        assert card.sla_score is None
        # The OVERALL snapshot row still records the run, with "No data" (actual = None)
        snap = VendorScorecardSLAMetric.objects.filter(scorecard=card)
        assert snap.count() == 1
        assert snap.get().metric_code == "OVERALL"
        assert snap.get().actual_pct is None and snap.get().breaches == 0

    def test_detail_page_renders_sla_section(self, client, procurement_world):
        w = procurement_world
        contract = _make_contract_with_obligations(w)
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        client.force_login(w["exec"])
        res = client.get(f"/scorecards/vendor/{w['vendor_a'].id}/")
        assert res.status_code == 200
        body = res.content.decode()
        assert "Contract SLA Scorecard" in body
        assert "CON-SLA-1" in body
        assert "Responsiveness" in body  # reported separately
        assert res.context["overall_row"].breaches == 1
        assert len(res.context["contract_rows"]) == 1
        assert res.context["contract_rows"][0].contract_id == contract.id

    def test_new_scorecard_calculate_writes_sla_rows_together(self, procurement_world):
        w = procurement_world
        _make_contract_with_obligations(w)
        from apps.scorecards.services import calculate_vendor_scorecard_service

        card = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        assert VendorScorecardSLAMetric.objects.filter(scorecard=card).count() == 2


# --------------------------------------------------------------------------
# 4. Cross-module sync: Vendor Master, Governance and API read scorecards values
# --------------------------------------------------------------------------


class TestCrossModuleSync:
    def test_vendor_master_reads_latest_scorecard(self, client, procurement_world):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        client.force_login(w["exec"])
        res = client.get(f"/vendors/{w['vendor_a'].id}/")
        assert res.status_code == 200
        latest = res.context["latest_scorecard"]
        assert latest.composite_score == 100
        assert latest.band_display == "Good"

    def test_governance_registers_are_scored_from_annotations(
        self, client, procurement_world
    ):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        calculate_vendor_scorecard_service(
            vendor=w["vendor_hold"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        client.force_login(w["exec"])
        res = client.get("/vendors/governance/")
        assert res.status_code == 200
        bands = {v.vendor_number: v.performance_band for v in res.context["page_obj"].object_list}
        assert bands[w["vendor_a"].vendor_number] == "good"
        # The held vendor only has the compliance indicator → score 60 → watch band starts at 70
        assert bands[w["vendor_hold"].vendor_number] == "issue"

    def test_vendor_api_reads_scorecard_fields(self, procurement_world):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        api = APIClient()
        api.force_authenticate(user=w["mgr"])
        res = api.get(f"/api/v1/vendors/{w['vendor_a'].id}/")
        assert res.status_code == 200
        data = res.json()
        assert data["latest_performance_score"] == 100
        assert data["latest_performance_period"] == "Q5-2026"
        assert data["performance_band"] == "GOOD"


# --------------------------------------------------------------------------
# 5. RBAC on supplier performance views and scorecards API
# --------------------------------------------------------------------------


class TestPerformanceRbac:
    def test_scorecard_detail_rbac(self, client, procurement_world):
        w = procurement_world
        client.force_login(w["requester"])
        assert client.get(f"/scorecards/vendor/{w['vendor_a'].id}/").status_code == 403
        client.force_login(w["auditor"])
        assert client.get(f"/scorecards/vendor/{w['vendor_a'].id}/").status_code == 200
        # Vendor portal user is not an internal scorecard role
        client.force_login(w["user_a"])
        assert client.get(f"/scorecards/vendor/{w['vendor_a'].id}/").status_code == 403
        client.logout()

    def test_scorecard_api_is_read_only_resource(self, procurement_world):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["exec"])
        res = api.post("/api/v1/scorecards/", {"vendor": str(w["vendor_a"].id)}, format="json")
        assert res.status_code == 405  # no arbitrary scorecard creation via PATCH-style POST
        card = VendorScorecard(
            vendor=w["vendor_a"], evaluation_period="Q4", evaluated_by=w["exec"]
        )
        card.save()
        res = api.patch(f"/api/v1/scorecards/{card.id}/", {"composite_score": 1}, format="json")
        assert res.status_code == 405
        res = api.delete(f"/api/v1/scorecards/{card.id}/")
        assert res.status_code == 405

    def test_scorecard_api_calculate_and_read_fields(self, procurement_world):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["exec"])
        res = api.post(
            "/api/v1/scorecards/calculate/",
            {"vendor_id": str(w["vendor_a"].id), "period": "Q4-9999"},
            format="json",
        )
        assert res.status_code == 201
        body = res.json()
        # No transactional indicator data → those stay "No data"; the ACTIVE compliance
        # status is the only indicator with data, so composite = 100.
        for field in ("delivery_score", "quality_score", "price_score", "responsiveness_score", "sla_score"):
            assert body[field] is None
        assert body["composite_score"] == "100.00"  # DecimalField serialised as string
        assert body["performance_status"] == "EXCELLENT"
        assert body["performance_band"] == "GOOD"
        assert body["band_display"] == "Good"
        res = api.get("/api/v1/scorecards/")
        assert res.status_code == 200
        fields = res.json()["results"][0]
        for field in ("responsiveness_score", "sla_score", "performance_band", "band_display"):
            assert field in fields

    def test_no_data_composite_reports_no_data(self):
        card = VendorScorecard(vendor=None, evaluation_period="Q1")
        # composite None (no indicators) → NO_DATA band, never fabricated
        assert card.performance_band == "NO_DATA"
        assert card.band_display == "No data"

    def test_calculate_and_list_rbac(self, procurement_world):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["auditor"])
        assert api.get("/api/v1/scorecards/").status_code == 200
        res = api.post(
            "/api/v1/scorecards/calculate/",
            {"vendor_id": str(w["vendor_a"].id), "period": "X"},
            format="json",
        )
        assert res.status_code == 403

    def test_calculate_roles_excludes_general_roles(self, procurement_world):
        w = procurement_world
        from apps.accounts.models import Role
        from apps.scorecards.permissions import can_calculate_scorecards

        assert can_calculate_scorecards(w["exec"]) and can_calculate_scorecards(w["mgr"])
        assert Role.AUDITOR not in SCORECARD_CALCULATE_ROLES
        assert Role.REQUESTER not in SCORECARD_CALCULATE_ROLES
        assert Role.VENDOR_USER not in SCORECARD_CALCULATE_ROLES


# --------------------------------------------------------------------------
# 6. Duplicate prevention: risk assessment / status APIs reuse the services
# --------------------------------------------------------------------------


class TestDuplicatesPrevention:
    def test_assess_risk_api_uses_service_and_audit(self, procurement_world):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["exec"])
        res = api.post(
            f"/api/v1/vendors/{w['vendor_a'].id}/assess-risk/",
            {"risk_level": "MEDIUM", "notes": "Via API", "risk_flags": ["FINANCIAL"]},
            format="json",
        )
        assert res.status_code == 200
        record = VendorRiskRecord.objects.get(id=res.json()["risk_record_id"])
        assert record.assessed_by == w["exec"]
        assert record.created_by == w["exec"]  # service stamped the author
        assert record.assessment_notes == "Via API"
        assert AuditLog.objects.filter(target_model="VendorRiskRecord").exists()

    def test_assess_risk_activation_without_kyc_is_blocked_by_service(
        self, procurement_world
    ):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["exec"])
        res = api.post(
            f"/api/v1/vendors/{w['vendor_kyc'].id}/assess-risk/",
            {"risk_level": "LOW", "notes": "Activate now", "governance_status": "ACTIVE"},
            format="json",
        )
        assert res.status_code == 400
        w["vendor_kyc"].refresh_from_db()
        assert w["vendor_kyc"].status == Vendor.STATUS_KYC_REVIEW  # KYC gate upheld

    def test_governance_status_api_no_inline_reject_override(self, procurement_world):
        w = procurement_world
        api = APIClient()
        api.force_authenticate(user=w["mgr"])
        res = api.post(
            f"/api/v1/vendors/{w['vendor_kyc'].id}/governance-status/",
            {"status": "REJECTED", "notes": "Reject via service path"},
            format="json",
        )
        assert res.status_code == 200
        w["vendor_kyc"].refresh_from_db()
        assert w["vendor_kyc"].status == Vendor.STATUS_REJECTED
        assert (
            w["vendor_kyc"].status_notes
            == "Reject via service path"  # transition table change audited by service
        )
        log = AuditLog.objects.filter(
            target_model="Vendor", target_object_id=str(w["vendor_kyc"].id)
        ).order_by("-timestamp").first()
        assert log.previous_state == {"status": Vendor.STATUS_KYC_REVIEW}

    def test_web_status_change_path_is_unchanged(self, client, procurement_world):
        w = procurement_world
        client.force_login(w["exec"])
        res = client.post(
            f"/vendors/{w['vendor_a'].id}/status/", {"status": "ON_HOLD", "notes": "x"}
        )
        assert res.status_code == 302
        w["vendor_a"].refresh_from_db()
        assert w["vendor_a"].status == Vendor.STATUS_ON_HOLD


# --------------------------------------------------------------------------
# 7. ON_HOLD vendors in sourcing: blocked, reactivation restores ability
# --------------------------------------------------------------------------


class TestHoldSuspensionNewSources:
    def test_hold_blocks_draft_and_submit(self, procurement_world):
        w = procurement_world
        event = _invite_and_publish(w, "Held vendor event")
        vendor = w["vendor_a"]
        set_vendor_status_governance_service(
            vendor=vendor, actor=w["mgr"], new_status="ON_HOLD", notes="Checks"
        )
        for call in (
            lambda: sourcing_svc.save_draft_bid_service(
                event=event, vendor=vendor, user=w["user_a"], line_items=_bid()
            ),
            lambda: sourcing_svc.submit_vendor_bid_service(
                event=event, vendor=vendor, submitted_by_user=w["user_a"], line_items=_bid()
            ),
        ):
            with pytest.raises(ValidationError, match="on hold"):
                call()

    def test_reactivating_restores_submitting(self, procurement_world):
        w = procurement_world
        event = _invite_and_publish(w, "Reactivation event")
        vendor = w["vendor_a"]
        set_vendor_status_governance_service(
            vendor=vendor, actor=w["mgr"], new_status="ON_HOLD", notes="Checks"
        )
        set_vendor_status_governance_service(
            vendor=vendor, actor=w["mgr"], new_status="ACTIVE", notes="Cleared"
        )
        bid = sourcing_svc.submit_vendor_bid_service(
            event=event, vendor=vendor, submitted_by_user=w["user_a"], line_items=_bid()
        )
        assert bid.status == "SUBMITTED"

    def test_blocked_amendment_before_close(self, procurement_world):
        w = procurement_world
        event = _invite_and_publish(w, "Amend held event")
        vendor = w["vendor_a"]
        bid = sourcing_svc.submit_vendor_bid_service(
            event=event, vendor=vendor, submitted_by_user=w["user_a"], line_items=_bid()
        )
        set_vendor_status_governance_service(
            vendor=vendor, actor=w["mgr"], new_status="ON_HOLD", notes="Checks"
        )
        with pytest.raises(ValidationError, match="on hold"):
            sourcing_svc.amend_vendor_bid_service(
                bid=bid,
                vendor_user=w["user_a"],
                amendment_reason="Price change",
                line_items=_bid(),
            )


# --------------------------------------------------------------------------
# 8. Historical preservation: runs are new rows, never overwritten
# --------------------------------------------------------------------------


class TestHistoryPreservation:
    def test_two_runs_are_two_rows_and_value_not_overwritten(self, procurement_world):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        first = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="P1", evaluated_by_user=w["exec"]
        )
        complianceP = first.compliance_score
        second = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="P2", evaluated_by_user=w["exec"]
        )
        assert VendorScorecard.objects.filter(vendor=w["vendor_a"]).count() == 2
        first.refresh_from_db()
        assert first.compliance_score == complianceP
        assert second.evaluation_period == "P2"

    def test_sla_snapshots_are_preserved_across_runs(self, procurement_world):
        w = procurement_world
        _make_contract_with_obligations(w)
        from apps.scorecards.services import calculate_vendor_scorecard_service

        card1 = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="P1", evaluated_by_user=w["exec"]
        )
        # Clear the unfulfilled breach by completing it before its due date
        ContractObligation.objects.filter(title="Renew certification").update(
            is_fulfilled=True, fulfilled_at=timezone.now() - timedelta(days=3)
        )
        card2 = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="P2", evaluated_by_user=w["exec"]
        )
        overall1 = VendorScorecardSLAMetric.objects.get(scorecard=card1, metric_code="OVERALL")
        overall2 = VendorScorecardSLAMetric.objects.get(scorecard=card2, metric_code="OVERALL")
        assert overall1.breaches == 1
        assert overall2.breaches == 0  # new run reflects new state
        overall1.refresh_from_db()
        assert overall1.breaches == 1  # history untouched


# --------------------------------------------------------------------------
# 9. Service lifecycle regressions in sourcing around award
# --------------------------------------------------------------------------


class TestAwardBlocksIneligible:
    def test_award_requires_active_vendor(self, procurement_world):
        from apps.scorecards.services import (  # noqa: F401
            calculate_vendor_scorecard_service,
        )
        from apps.sourcing.services import _assert_vendor_awardable

        _make_contract_with_obligations(procurement_world)
        w = procurement_world
        with pytest.raises(ValidationError, match="cannot be awarded"):
            _assert_vendor_awardable(w["vendor_susp"])
        with pytest.raises(ValidationError, match="cannot be awarded"):
            _assert_vendor_awardable(w["vendor_hold"])


# --------------------------------------------------------------------------
# 10. The manager risk desk stays a read-only consumer
# --------------------------------------------------------------------------


class TestManagerConsumes:
    def test_manager_performance_page_and_api_read_scorecards(
        self, client, procurement_world
    ):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-2026", evaluated_by_user=w["exec"]
        )
        client.force_login(w["mgr"])
        res = client.get("/manager/performance/")
        assert res.status_code == 200
        api = APIClient()
        api.force_authenticate(user=w["mgr"])
        data = api.get("/manager/api/performance/").json()
        names = [row["vendor_name"] for row in data["scorecards"]]
        assert any("Alpha Hardware Ltd" in name for name in names)

    def test_scorecard_write_paths_only_via_scorecards_app(self, procurement_world):
        w = procurement_world
        from apps.scorecards.services import calculate_vendor_scorecard_service

        card = calculate_vendor_scorecard_service(
            vendor=w["vendor_a"], evaluation_period="Q5-Z", evaluated_by_user=w["exec"]
        )
        from apps.scorecards.services import latest_scorecards_queryset

        for latest in latest_scorecards_queryset():
            if latest.vendor_id == w["vendor_a"].id:
                assert latest.id == card.id
                # the latest card carries all scorecards-owned display helpers
                assert hasattr(latest, "band_display")
                assert hasattr(latest, "indicator_rows")
                break
        else:
            pytest.fail("Vendor's latest scorecard missing from latest_scorecards_queryset")
