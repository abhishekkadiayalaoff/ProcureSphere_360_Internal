from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.contracts.models import Contract, ContractVersion
from apps.contracts.services import (
    activate_contract_service,
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
)
from apps.vendors.models import VendorCategory
from apps.vendors.services import register_vendor_service


@pytest.fixture
def contract_setup(db):
    legal_role, _ = Role.objects.get_or_create(
        code=Role.LEGAL_MGR, defaults={"name": "Legal Manager"}
    )
    proc_role, _ = Role.objects.get_or_create(
        code=Role.PROC_MGR, defaults={"name": "Procurement Manager"}
    )
    requester_role, _ = Role.objects.get_or_create(
        code=Role.REQUESTER, defaults={"name": "Requester"}
    )

    legal_user = User.objects.create_user(
        email="legal.mgr@hpe.com", password="Password123!", role=legal_role
    )
    proc_user = User.objects.create_user(
        email="proc.mgr@hpe.com", password="Password123!", role=proc_role
    )
    requester_user = User.objects.create_user(
        email="requester@hpe.com", password="Password123!", role=requester_role
    )

    category = VendorCategory.objects.create(name="IT Services", code="CAT-IT-01")
    vendor = register_vendor_service(
        legal_name="Enterprise Cloud Solutions Inc",
        tax_identification_number="TAX-ECS-999",
        category=category,
        email="legal@cloudsolutions.com",
        address="100 Technology Way",
    )

    today = timezone.now().date()
    contract = create_contract_service(
        title="Enterprise Data Center Maintenance Agreement",
        vendor=vendor,
        contract_value=Decimal("250000.00"),
        start_date=today,
        end_date=today + timezone.timedelta(days=365),
        renewal_notice_days=30,
        contract_owner=legal_user,
    )

    return {
        "legal_user": legal_user,
        "proc_user": proc_user,
        "requester_user": requester_user,
        "vendor": vendor,
        "contract": contract,
    }


@pytest.mark.django_db
def test_contract_legal_and_business_approval_workflow(contract_setup):
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]

    assert contract.status == Contract.STATUS_DRAFT
    assert contract.version == 1

    # 1. Submit for Legal Review
    contract = submit_for_legal_review_service(
        contract=contract, user=legal_user, notes="Urgent legal review required"
    )
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # 2. Approve Legal Review
    contract = approve_legal_review_service(
        contract=contract, user=legal_user, notes="Terms and indemnity clauses verified"
    )
    assert contract.status == Contract.STATUS_BUSINESS_APPROVAL

    # 3. Approve Business & Activate
    contract = approve_business_service(
        contract=contract, user=proc_user, notes="Budget allocated and signed off"
    )
    assert contract.status == Contract.STATUS_ACTIVE


@pytest.mark.django_db
def test_contract_legal_rejection_workflow(contract_setup):
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]

    submit_for_legal_review_service(contract=contract, user=legal_user)
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    contract = reject_legal_review_service(
        contract=contract, user=legal_user, reason="Missing compliance Annexure B"
    )
    assert contract.status == Contract.STATUS_DRAFT


@pytest.mark.django_db
def test_contract_version_amendment_preserves_history(contract_setup):
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]

    today = timezone.now().date()
    # Create Amendment -> Version 2
    version2 = create_contract_version_service(
        contract=contract,
        user=legal_user,
        amendment_summary="Expanded service scope to include Disaster Recovery site",
        contract_value=Decimal("320000.00"),
        start_date=today,
        end_date=today + timezone.timedelta(days=365),
    )

    contract.refresh_from_db()
    assert contract.version == 2
    assert contract.contract_value == Decimal("320000.00")
    assert version2.version_number == 2
    assert ContractVersion.objects.filter(contract=contract).count() == 2


@pytest.mark.django_db
def test_contract_milestones_and_obligations(contract_setup):
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    today = timezone.now().date()

    # Milestone
    milestone = add_contract_milestone_service(
        contract=contract,
        title="Phase 1 SLA Audit",
        due_date=today + timezone.timedelta(days=30),
        amount=Decimal("50000.00"),
    )
    assert not milestone.is_completed

    milestone = complete_contract_milestone_service(milestone=milestone, user=legal_user)
    assert milestone.is_completed

    # Obligation
    obligation = add_contract_obligation_service(
        contract=contract,
        title="Quarterly SOC2 Type II Report",
        responsible_party="VENDOR",
        due_date=today + timezone.timedelta(days=90),
    )
    assert not obligation.is_fulfilled

    obligation = fulfill_contract_obligation_service(obligation=obligation, user=legal_user)
    assert obligation.is_fulfilled


@pytest.mark.django_db
def test_contract_renewal_and_termination(contract_setup):
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    today = timezone.now().date()

    # Activate contract first
    contract = activate_contract_service(contract=contract, user=legal_user)
    assert contract.status == Contract.STATUS_ACTIVE

    # Renew
    contract = renew_contract_service(
        contract=contract,
        user=legal_user,
        new_end_date=today + timezone.timedelta(days=730),
        new_value=Decimal("500000.00"),
        notes="Option year exercised",
    )
    assert contract.status == Contract.STATUS_RENEWED
    assert contract.contract_value == Decimal("500000.00")

    # Terminate
    contract = terminate_contract_service(
        contract=contract, user=legal_user, reason="Convenience termination clause exercised"
    )
    assert contract.status == Contract.STATUS_TERMINATED


@pytest.mark.django_db
def test_legal_manager_dashboard_and_views(client, contract_setup):
    legal_user = contract_setup["legal_user"]
    contract = contract_setup["contract"]

    client.force_login(legal_user)

    # 1. Dashboard View
    response = client.get("/")
    assert response.status_code == 200
    assert (
        "Legal &amp; Contracts" in response.content.decode() or "Legal" in response.content.decode()
    )

    # 2. Contract Register List View
    response = client.get(reverse("contracts_list"))
    assert response.status_code == 200
    assert contract.contract_number in response.content.decode()

    # 3. Contract Detail View
    response = client.get(reverse("contract_detail", kwargs={"contract_id": contract.id}))
    assert response.status_code == 200
    assert contract.title in response.content.decode()
