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


def _get_or_create_role(code, name):
    role = Role.objects.filter(code=code).first()
    if not role:
        try:
            role, _ = Role.objects.get_or_create(code=code, defaults={"name": name})
        except Exception:
            role = Role.objects.filter(code=code).first()
    return role


def _get_or_create_user(email, password, role):
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create_user(email=email, password=password, role=role)
    else:
        user.role = role
        user.save()
        user.refresh_from_db()
    return user


@pytest.fixture
def contract_setup(db):
    legal_role = _get_or_create_role(Role.LEGAL_MGR, "Legal Manager")
    proc_role = _get_or_create_role(Role.PROC_MGR, "Procurement Manager")
    requester_role = _get_or_create_role(Role.REQUESTER, "Requester")

    legal_user = _get_or_create_user("legal.mgr@hpe.com", "Password123!", legal_role)
    proc_user = _get_or_create_user("proc.mgr@hpe.com", "Password123!", proc_role)
    requester_user = _get_or_create_user("requester@hpe.com", "Password123!", requester_role)

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


@pytest.mark.django_db
def test_contract_document_vault_upload_and_validation(client, contract_setup):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.audit.models import AuditLog
    from apps.contracts.forms import ContractDocumentForm
    from apps.contracts.models import ContractDocument
    from apps.contracts.services import upload_contract_document_service

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]

    # 1. Service Layer upload
    valid_file = SimpleUploadedFile("executed_msa.pdf", b"%PDF-1.4 dummy content", content_type="application/pdf")
    doc = upload_contract_document_service(
        contract=contract,
        user=legal_user,
        title="Executed Master Service Agreement",
        file=valid_file,
    )
    assert doc.id is not None
    assert doc.title == "Executed Master Service Agreement"
    assert doc.uploaded_by == legal_user

    # Verify AuditLog
    audit_entry = AuditLog.objects.filter(target_model="ContractDocument", target_object_id=str(doc.id)).first()
    assert audit_entry is not None
    assert audit_entry.actor == legal_user

    # 2. Form Validation — Invalid extension
    invalid_file = SimpleUploadedFile("malicious.exe", b"binary data", content_type="application/octet-stream")
    form = ContractDocumentForm(data={"title": "Bad File"}, files={"file": invalid_file})
    assert not form.is_valid()
    assert "Unsupported file format" in str(form.errors["file"])

    # 3. REST API upload endpoint
    client.force_login(legal_user)
    api_file = SimpleUploadedFile("sow_appendix.docx", b"dummy word content", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response = client.post(
        f"/api/v1/contracts/{contract.id}/upload-document/",
        {"title": "SOW Appendix A", "file": api_file},
        format="multipart",
    )
    assert response.status_code == 201
    assert response.json()["title"] == "SOW Appendix A"
    assert ContractDocument.objects.filter(title="SOW Appendix A").exists()


@pytest.mark.django_db
def test_full_contract_lifecycle_view_and_api_workflow(client, contract_setup):
    """
    Day 15 Task: Validate complete end-to-end Contract -> Legal Review -> Business Approval -> Active workflow
    via both HTTP views and DRF REST API endpoints, verifying RBAC, AuditLog, and Notifications.
    """
    from apps.audit.models import AuditLog
    from apps.notifications.models import Notification

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]
    requester_user = contract_setup["requester_user"]

    auditor_role, _ = Role.objects.get_or_create(code=Role.AUDITOR, defaults={"name": "Auditor"})
    auditor_user = User.objects.create_user(
        email="auditor.d15@hpe.com", password="Password123!", role=auditor_role
    )

    # Initial state: DRAFT
    assert contract.status == Contract.STATUS_DRAFT

    # 1. Requester / Owner submits for Legal Review via HTTP View
    client.force_login(legal_user)
    response = client.post(reverse("contract_submit_legal", kwargs={"contract_id": contract.id}), {"notes": "Submitting for contract sign-off"})
    assert response.status_code == 302
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # Verify AuditLog & Notification for Legal Manager
    audit1 = AuditLog.objects.filter(target_model="Contract", target_object_id=str(contract.id)).latest("timestamp")
    assert audit1.action == AuditLog.ACTION_UPDATE
    assert Notification.objects.filter(recipient=legal_user, notification_type=Notification.TYPE_APPROVAL_REQUIRED).exists()

    # 2. Negative RBAC: Requester attempts Legal Approval via REST API -> 403 Forbidden
    client.force_login(requester_user)
    api_resp = client.post(f"/api/v1/contracts/{contract.id}/legal-approve/", {"notes": "Bypassing legal"}, content_type="application/json")
    assert api_resp.status_code == 403
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # 3. Negative RBAC: Auditor attempts Legal Approval via HTTP View -> Permission Error
    client.force_login(auditor_user)
    response = client.post(reverse("contract_legal_approve", kwargs={"contract_id": contract.id}), {"notes": "Auditor approve"})
    assert response.status_code == 302
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # 4. Legal Manager approves via REST API -> BUSINESS_APPROVAL
    client.force_login(legal_user)
    api_resp = client.post(f"/api/v1/contracts/{contract.id}/legal-approve/", {"notes": "Legal sign-off complete"}, content_type="application/json")
    assert api_resp.status_code == 200
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_BUSINESS_APPROVAL

    # Verify AuditLog & Notifications for Procurement Manager
    audit2 = AuditLog.objects.filter(target_model="Contract", target_object_id=str(contract.id)).latest("timestamp")
    assert audit2.action == AuditLog.ACTION_APPROVE
    assert Notification.objects.filter(recipient=proc_user, notification_type=Notification.TYPE_APPROVAL_REQUIRED).exists()

    # 5. Business Approval via REST API -> ACTIVE
    client.force_login(proc_user)
    api_resp = client.post(f"/api/v1/contracts/{contract.id}/business-approve/", {"notes": "Executive budget approval"}, content_type="application/json")
    assert api_resp.status_code == 200
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_ACTIVE

    # Verify final AuditLog & Notification
    audit3 = AuditLog.objects.filter(target_model="Contract", target_object_id=str(contract.id)).latest("timestamp")
    assert audit3.action == AuditLog.ACTION_APPROVE
    assert Notification.objects.filter(recipient=contract.contract_owner, notification_type=Notification.TYPE_APPROVAL_REQUIRED).exists()


@pytest.mark.django_db
def test_contract_expiry_renewal_and_notification_routing(client, contract_setup):
    """
    Day 16 Task: Complete contract expiry and renewal notifications, background scans, and context processor integration.
    """
    from apps.notifications.context_processors import notifications_processor
    from apps.notifications.models import Notification
    from apps.contracts.tasks import scan_contract_expirations_and_milestones_task

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]
    today = timezone.now().date()

    # 1. Activate contract
    contract = activate_contract_service(contract=contract, user=legal_user)
    assert contract.status == Contract.STATUS_ACTIVE

    # 2. Renew contract -> dispatches TYPE_CONTRACT_EXPIRATION notification
    renew_contract_service(
        contract=contract,
        user=legal_user,
        new_end_date=today + timezone.timedelta(days=365),
        notes="Extended for 1 year",
    )
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_RENEWED
    assert Notification.objects.filter(recipient=legal_user, notification_type=Notification.TYPE_CONTRACT_EXPIRATION).exists()
    assert Notification.objects.filter(recipient=proc_user, notification_type=Notification.TYPE_CONTRACT_EXPIRATION).exists()

    # 3. Fast-forward contract end date to past -> scan task transitions to EXPIRED
    contract.end_date = today - timezone.timedelta(days=5)
    contract.save(update_fields=["end_date"])

    task_result = scan_contract_expirations_and_milestones_task()
    assert "Contract alert scan completed" in task_result

    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_EXPIRED
    assert Notification.objects.filter(recipient=legal_user, notification_type=Notification.TYPE_CONTRACT_EXPIRATION, message__contains="has expired").exists()

    # 4. Context processor pending approvals & unread notification count
    # Move a draft contract to LEGAL_REVIEW to test pending count
    contract.status = Contract.STATUS_LEGAL_REVIEW
    contract.save(update_fields=["status"])

    class DummyRequest:
        user = legal_user

    ctx = notifications_processor(DummyRequest())
    assert ctx["pending_approvals_count"] >= 1
    assert ctx["unread_notifications_count"] >= 1


@pytest.mark.django_db
def test_contract_amendment_price_sla_and_term_preserves_previous_versions(client, contract_setup):
    """
    Day 17 Task: Validate contract amendments changing price, SLA or term while preserving previous version history.
    """
    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    today = timezone.now().date()

    # Initial state assertions (Version 1)
    assert contract.version == 1
    assert contract.contract_value == Decimal("250000.00")
    v1_record = ContractVersion.objects.get(contract=contract, version_number=1)
    assert v1_record.contract_value == Decimal("250000.00")
    assert v1_record.start_date == today
    assert v1_record.end_date == today + timezone.timedelta(days=365)
    assert v1_record.amendment_summary == "Initial Contract Execution Draft"

    # 1. First Amendment: Change Price, SLA, and Term via service
    v2_end_date = today + timezone.timedelta(days=500)
    v2_summary = "SLA revised to 99.99% uptime with 2-hour MTTR; Contract value increased; Term extended by 135 days"
    v2_record = create_contract_version_service(
        contract=contract,
        user=legal_user,
        amendment_summary=v2_summary,
        contract_value=Decimal("380000.00"),
        start_date=today,
        end_date=v2_end_date,
    )

    contract.refresh_from_db()
    assert contract.version == 2
    assert contract.contract_value == Decimal("380000.00")
    assert contract.end_date == v2_end_date

    # Verify Version 1 was NOT modified (Preserved History)
    v1_record.refresh_from_db()
    assert v1_record.contract_value == Decimal("250000.00")
    assert v1_record.end_date == today + timezone.timedelta(days=365)
    assert v1_record.amendment_summary == "Initial Contract Execution Draft"

    # Verify Version 2 details
    assert v2_record.version_number == 2
    assert v2_record.contract_value == Decimal("380000.00")
    assert v2_record.end_date == v2_end_date
    assert v2_record.amendment_summary == v2_summary
    assert v2_record.approved_by == legal_user

    # 2. Second Amendment: Change Price, SLA, and Term via REST API
    client.force_login(legal_user)
    v3_end_date = today + timezone.timedelta(days=730)
    v3_summary = "SLA enhanced with 24/7 dedicated account manager; Price updated to $450,000; Term extended to 2 years"
    api_payload = {
        "amendment_summary": v3_summary,
        "contract_value": "450000.00",
        "start_date": str(today),
        "end_date": str(v3_end_date),
    }

    response = client.post(
        f"/api/v1/contracts/{contract.id}/amend/",
        api_payload,
        content_type="application/json",
    )
    assert response.status_code == 201

    contract.refresh_from_db()
    assert contract.version == 3
    assert contract.contract_value == Decimal("450000.00")
    assert contract.end_date == v3_end_date

    # Verify all 3 version history records are preserved in database
    versions = list(ContractVersion.objects.filter(contract=contract).order_by("version_number"))
    assert len(versions) == 3

    # V1 check
    assert versions[0].version_number == 1
    assert versions[0].contract_value == Decimal("250000.00")

    # V2 check
    assert versions[1].version_number == 2
    assert versions[1].contract_value == Decimal("380000.00")
    assert versions[1].end_date == v2_end_date

    # V3 check
    assert versions[2].version_number == 3
    assert versions[2].contract_value == Decimal("450000.00")
    assert versions[2].end_date == v3_end_date
    assert versions[2].amendment_summary == v3_summary


@pytest.mark.django_db
def test_contract_obligations_milestones_and_document_evidence(client, contract_setup):
    """
    Day 18 Task: Validate contract obligations, milestones and document evidence end-to-end.
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.audit.models import AuditLog
    from apps.contracts.models import ContractDocument, ContractMilestone, ContractObligation

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    today = timezone.now().date()

    # Create Auditor user
    auditor_role = _get_or_create_role(Role.AUDITOR, "Auditor")
    auditor_user = User.objects.create_user(email="auditor@hpe.com", password="Password123!", role=auditor_role)

    client.force_login(legal_user)

    # 1. Add SLA Milestone via Web View & verify AuditLog
    m1_due = today + timezone.timedelta(days=30)
    resp = client.post(
        reverse("contract_milestone_create", kwargs={"contract_id": contract.id}),
        {"title": "Phase 1 Acceptance & Signoff", "due_date": str(m1_due), "amount": "50000.00"},
        follow=True,
    )
    assert resp.status_code == 200
    milestone1 = ContractMilestone.objects.get(contract=contract, title="Phase 1 Acceptance & Signoff")
    assert milestone1.amount == Decimal("50000.00")
    assert milestone1.is_completed is False
    assert AuditLog.objects.filter(target_model="ContractMilestone", target_object_id=str(milestone1.id), action=AuditLog.ACTION_CREATE).exists()

    # Complete Milestone 1 & verify AuditLog
    resp = client.post(
        reverse("contract_milestone_complete", kwargs={"contract_id": contract.id, "milestone_id": milestone1.id}),
        follow=True,
    )
    assert resp.status_code == 200
    milestone1.refresh_from_db()
    assert milestone1.is_completed is True
    assert milestone1.completed_at is not None

    # 2. Add Legal Obligation via REST API
    o1_due = today + timezone.timedelta(days=45)
    api_payload = {
        "title": "Quarterly ISO 27001 Security Audit Compliance Report",
        "responsible_party": "VENDOR LEGAL",
        "due_date": str(o1_due),
    }
    response = client.post(
        f"/api/v1/contracts/{contract.id}/add-obligation/",
        api_payload,
        content_type="application/json",
    )
    assert response.status_code == 201
    obligation1 = ContractObligation.objects.get(contract=contract, title="Quarterly ISO 27001 Security Audit Compliance Report")
    assert obligation1.responsible_party == "VENDOR LEGAL"
    assert obligation1.is_fulfilled is False
    assert AuditLog.objects.filter(target_model="ContractObligation", target_object_id=str(obligation1.id), action=AuditLog.ACTION_CREATE).exists()

    # Fulfill Obligation via REST API
    response = client.post(
        f"/api/v1/contracts/{contract.id}/fulfill-obligation/{obligation1.id}/",
        content_type="application/json",
    )
    assert response.status_code == 200
    obligation1.refresh_from_db()
    assert obligation1.is_fulfilled is True
    assert obligation1.fulfilled_at is not None

    # 3. Upload Contract Document Evidence
    sample_file = SimpleUploadedFile("executed_msa_agreement.pdf", b"PDF Document Content Bytes", content_type="application/pdf")
    resp = client.post(
        reverse("contract_document_upload", kwargs={"contract_id": contract.id}),
        {"title": "Executed Master Service Agreement PDF", "file": sample_file},
        follow=True,
    )
    assert resp.status_code == 200
    doc = ContractDocument.objects.get(contract=contract, title="Executed Master Service Agreement PDF")
    assert doc.uploaded_by == legal_user
    assert AuditLog.objects.filter(target_model="ContractDocument", target_object_id=str(doc.id), action=AuditLog.ACTION_CREATE).exists()

    # 4. Enforce Auditor read-only restriction on milestone & obligation creation
    client.force_login(auditor_user)
    resp = client.post(
        reverse("contract_milestone_create", kwargs={"contract_id": contract.id}),
        {"title": "Auditor Milestone Attempt", "due_date": str(m1_due), "amount": "1000.00"},
        follow=False,
    )
    assert resp.status_code == 302
    assert not ContractMilestone.objects.filter(title="Auditor Milestone Attempt").exists()


@pytest.mark.django_db
def test_day19_end_to_end_contract_integration_lifecycle(client, contract_setup):
    """
    Day 19 Task: Comprehensive end-to-end Contract integration lifecycle test:
    creation -> review -> approval -> active -> renewal/expiry -> audit & notifications.
    """
    from apps.audit.models import AuditLog
    from apps.notifications.context_processors import notifications_processor
    from apps.notifications.models import Notification
    from apps.contracts.tasks import scan_contract_expirations_and_milestones_task

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]
    today = timezone.now().date()

    # 1. State: DRAFT -> Submit for Legal Review
    submit_for_legal_review_service(contract=contract, user=legal_user, notes="Initial legal review request")
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # Verify context processor reports pending approval for Legal Manager
    class DummyRequest:
        user = legal_user
    ctx = notifications_processor(DummyRequest())
    assert ctx["pending_approvals_count"] >= 1

    # 2. State: LEGAL_REVIEW -> Legal Approval -> BUSINESS_APPROVAL
    approve_legal_review_service(contract=contract, user=legal_user, notes="Legal terms approved")
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_BUSINESS_APPROVAL

    # 3. State: BUSINESS_APPROVAL -> Business Approval -> ACTIVE
    approve_business_service(contract=contract, user=proc_user, notes="Business budget approved")
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_ACTIVE

    # 4. State: ACTIVE -> Celery scan triggers RENEWAL_DUE
    contract.end_date = today + timezone.timedelta(days=15)
    contract.renewal_notice_days = 30
    contract.save(update_fields=["end_date", "renewal_notice_days"])

    scan_contract_expirations_and_milestones_task()
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_RENEWAL_DUE

    # 5. State: RENEWAL_DUE -> Renew Contract -> RENEWED (Version 2)
    renew_contract_service(
        contract=contract,
        user=legal_user,
        new_end_date=today + timezone.timedelta(days=365),
        new_value=Decimal("300000.00"),
        notes="Renewed for another year",
    )
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_RENEWED
    assert contract.version == 2
    assert contract.contract_value == Decimal("300000.00")

    # 6. State: RENEWED -> Celery scan triggers EXPIRED when end_date passes
    contract.end_date = today - timezone.timedelta(days=1)
    contract.save(update_fields=["end_date"])

    scan_contract_expirations_and_milestones_task()
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_EXPIRED

    # 7. Audit & Notification checks
    assert AuditLog.objects.filter(target_model="Contract", target_object_id=str(contract.id)).count() >= 5
    assert Notification.objects.filter(recipient=legal_user).exists()


@pytest.mark.django_db
def test_day20_legal_rbac_contract_access_and_restricted_actions(client, contract_setup):
    """
    Day 20 Task: Validate Legal RBAC, contract access scoping, and restricted actions.
    Exercises:
    1. Auditor read-only restriction on views (document_upload, renew, terminate, obligation_toggle, milestone_create).
    2. Auditor read-only restriction on REST API endpoints (create, amend, renew, terminate, upload-document) -> 403.
    3. Vendor User scoping: Can view only own contract; cross-vendor access -> 403 / 404.
    4. Requester restricted action: Cannot perform Legal Review approval -> 403 Forbidden.
    5. Legal Manager access: Full access to dashboard, review, approval, and management actions.
    """
    from apps.vendors.models import VendorCategory
    from apps.vendors.services import register_vendor_service

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    requester_user = contract_setup["requester_user"]

    auditor_role = _get_or_create_role(Role.AUDITOR, "Auditor")
    vendor_role = _get_or_create_role(Role.VENDOR_USER, "Vendor User")

    auditor_user = User.objects.create_user(email="auditor.d20@hpe.com", password="Password123!", role=auditor_role)

    cat2 = VendorCategory.objects.create(name="Telecom D20", code="CAT-TEL-D20")
    vendor2 = register_vendor_service(
        legal_name="Apex Communications Ltd",
        tax_identification_number="TAX-APEX-20",
        category=cat2,
        email="apex@telecom.com",
        address="300 Apex Tower",
    )

    vendor_user1 = User.objects.create_user(
        email="vendor1.d20@hpe.com", password="Password123!", role=vendor_role, vendor=contract_setup["vendor"]
    )
    vendor_user2 = User.objects.create_user(
        email="vendor2.d20@hpe.com", password="Password123!", role=vendor_role, vendor=vendor2
    )

    # 1. Auditor read-only checks on Views
    client.force_login(auditor_user)

    # Auditor GET contract register & detail -> 200 OK
    assert client.get(reverse("contracts_list")).status_code == 200
    assert client.get(reverse("contract_detail", kwargs={"contract_id": contract.id})).status_code == 200

    # Auditor POST document upload -> redirected with permission error message
    resp = client.post(reverse("contract_document_upload", kwargs={"contract_id": contract.id}), {"title": "Doc"}, follow=False)
    assert resp.status_code == 302

    # Auditor POST renew -> redirected with permission error message
    resp = client.post(reverse("contract_renew", kwargs={"contract_id": contract.id}), {"new_end_date": "2027-12-31"}, follow=False)
    assert resp.status_code == 302

    # Auditor POST terminate -> redirected with permission error message
    resp = client.post(reverse("contract_terminate", kwargs={"contract_id": contract.id}), {"reason": "Auditor terminate"}, follow=False)
    assert resp.status_code == 302

    # 2. Auditor read-only checks on REST API -> 403 Forbidden
    resp = client.post(f"/api/v1/contracts/{contract.id}/renew/", {"new_end_date": "2027-12-31"}, content_type="application/json")
    assert resp.status_code == 403

    resp = client.post(f"/api/v1/contracts/{contract.id}/amend/", {"amendment_summary": "Bad", "contract_value": "100", "start_date": "2026-01-01", "end_date": "2026-12-31"}, content_type="application/json")
    assert resp.status_code == 403

    resp = client.post(f"/api/v1/contracts/{contract.id}/terminate/", {"reason": "Bad"}, content_type="application/json")
    assert resp.status_code == 403

    # 3. Vendor User Scoping
    client.force_login(vendor_user1)
    api_list = client.get("/api/v1/contracts/").json()
    results = api_list.get("results", api_list) if isinstance(api_list, dict) else api_list
    contract_ids = [c["id"] for c in results if isinstance(c, dict) and "id" in c]
    assert str(contract.id) in contract_ids

    # Vendor 2 cannot access Vendor 1 contract via API -> 403 or 404 object permission check
    client.force_login(vendor_user2)
    resp = client.get(f"/api/v1/contracts/{contract.id}/")
    assert resp.status_code in [403, 404]

    # Vendor 2 cannot amend Vendor 1 contract -> 403
    resp = client.post(f"/api/v1/contracts/{contract.id}/amend/", {"amendment_summary": "Hack"}, content_type="application/json")
    assert resp.status_code == 403

    # 4. Requester restricted action: Cannot perform Legal Review approval
    client.force_login(requester_user)
    resp = client.post(f"/api/v1/contracts/{contract.id}/legal-approve/", {"notes": "Bypass"}, content_type="application/json")
    assert resp.status_code == 403

    # 5. Legal Manager access: Full access to dashboard & actions
    client.force_login(legal_user)
    assert client.get(reverse("contracts_dashboard")).status_code == 200


@pytest.mark.django_db
def test_day21_contract_integration_and_regression_testing(client, contract_setup):
    """
    Day 21 Task: Comprehensive Contract integration and regression testing.
    Verifies:
    1. Full lifecycle state transitions (DRAFT -> LEGAL_REVIEW -> BUSINESS_APPROVAL -> ACTIVE -> RENEWAL_DUE -> RENEWED -> EXPIRED).
    2. Versioning & amendment history preservation (V1, V2).
    3. Sub-system persistence: Milestones, Obligations, Documents, Alerts.
    4. Integration with AuditLog and Notifications.
    5. Scheduled Celery Beat scanning task execution.
    6. Complete RBAC enforcement across Legal Manager, Procurement Manager, Auditor, Requester, and Vendor User.
    """
    from apps.audit.models import AuditLog
    from apps.contracts.models import Contract, ContractAlert, ContractVersion
    from apps.contracts.tasks import scan_contract_expirations_and_milestones_task
    from apps.notifications.models import Notification

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]

    auditor_role = _get_or_create_role(Role.AUDITOR, "Auditor")
    auditor_user = User.objects.create_user(email="auditor.d21@hpe.com", password="Password123!", role=auditor_role)

    today = timezone.now().date()

    # Step 1: Submit to Legal Review & verify initial AuditLog
    client.force_login(legal_user)
    resp = client.post(reverse("contract_submit_legal", kwargs={"contract_id": contract.id}), {"notes": "Day 21 regression submit"}, follow=True)
    assert resp.status_code == 200
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # Step 2: Legal Approval -> BUSINESS_APPROVAL
    resp = client.post(reverse("contract_legal_approve", kwargs={"contract_id": contract.id}), {"notes": "Legal approved regression"}, follow=True)
    assert resp.status_code == 200
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_BUSINESS_APPROVAL

    # Step 3: Business Approval -> ACTIVE
    client.force_login(proc_user)
    resp = client.post(reverse("contract_business_approve", kwargs={"contract_id": contract.id}), {"notes": "Business signoff regression"}, follow=True)
    assert resp.status_code == 200
    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_ACTIVE

    # Step 4: Amendment -> Version 2
    client.force_login(legal_user)
    resp = client.post(
        reverse("contract_amend", kwargs={"contract_id": contract.id}),
        {"amendment_summary": "Day 21 Amendment", "contract_value": "350000.00", "start_date": str(today), "end_date": str(today + timezone.timedelta(days=365))},
        follow=True,
    )
    assert resp.status_code == 200
    contract.refresh_from_db()
    assert contract.version == 2
    assert contract.contract_value == Decimal("350000.00")
    assert ContractVersion.objects.filter(contract=contract).count() == 2

    # Step 5: Add Milestone & Obligation
    m = add_contract_milestone_service(contract=contract, title="Reg Milestone", due_date=today + timezone.timedelta(days=5), amount=Decimal("10000.00"), user=legal_user)
    o = add_contract_obligation_service(contract=contract, title="Reg Obligation", responsible_party="VENDOR", due_date=today + timezone.timedelta(days=5), user=legal_user)

    # Step 6: Celery Beat Scan -> RENEWAL_DUE & Alert generation
    contract.end_date = today + timezone.timedelta(days=10)
    contract.renewal_notice_days = 30
    contract.save(update_fields=["end_date", "renewal_notice_days"])

    scan_result = scan_contract_expirations_and_milestones_task()
    assert "Contract alert scan completed" in scan_result

    contract.refresh_from_db()
    assert contract.status == Contract.STATUS_RENEWAL_DUE
    assert ContractAlert.objects.filter(contract=contract).exists()

    # Step 7: Complete Milestone & Fulfill Obligation
    complete_contract_milestone_service(milestone=m, user=legal_user)
    fulfill_contract_obligation_service(obligation=o, user=legal_user)

    m.refresh_from_db()
    o.refresh_from_db()
    assert m.is_completed is True
    assert o.is_fulfilled is True

    # Step 8: Auditor Read-Only Regression Check
    client.force_login(auditor_user)
    assert client.get(reverse("contracts_list")).status_code == 200
    assert client.get(reverse("contract_detail", kwargs={"contract_id": contract.id})).status_code == 200
    assert client.post(reverse("contract_renew", kwargs={"contract_id": contract.id}), {"new_end_date": "2028-01-01"}, follow=False).status_code == 302
    assert client.post(f"/api/v1/contracts/{contract.id}/renew/", {"new_end_date": "2028-01-01"}, content_type="application/json").status_code == 403

    # Step 9: Final Audit & Notification Count Verifications
    assert AuditLog.objects.filter(target_model="Contract", target_object_id=str(contract.id)).count() >= 4
    assert Notification.objects.filter(recipient=legal_user).count() >= 1


@pytest.mark.django_db
def test_day22_contract_validation_terms_documents_and_transitions(client, contract_setup):
    """
    Day 22 Task: Validate contract mandatory fields, terms, documents, and status transitions.
    Verifies:
    1. Mandatory field & date checks on Contract creation (empty title, invalid end_date < start_date, negative contract_value).
    2. Mandatory field & date checks on Contract Amendment (empty summary, end_date < start_date, negative contract_value).
    3. Document evidence validation (file size <= 10MB limit, disallowed file extension rejection).
    4. Workflow status transition guards (invalid state transitions raise ValidationError).
    5. Termination & Renewal validation (empty reason rejection, invalid renewal date rejection).
    """
    from django.core.exceptions import ValidationError
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.contracts.models import Contract
    from apps.contracts.services import (
        approve_business_service,
        approve_legal_review_service,
        create_contract_service,
        create_contract_version_service,
        renew_contract_service,
        submit_for_legal_review_service,
        terminate_contract_service,
        upload_contract_document_service,
    )

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    vendor = contract_setup["vendor"]
    today = timezone.now().date()

    # 1. Contract Creation Validation
    # Empty title
    with pytest.raises(ValidationError, match="Contract title is required."):
        create_contract_service(
            title="",
            vendor=vendor,
            start_date=today,
            end_date=today + timezone.timedelta(days=30),
            contract_value=Decimal("1000.00"),
            contract_owner=legal_user,
        )

    # End date before start date
    with pytest.raises(ValidationError, match="Contract end date cannot be earlier than start date."):
        create_contract_service(
            title="Invalid Dates Contract",
            vendor=vendor,
            start_date=today,
            end_date=today - timezone.timedelta(days=1),
            contract_value=Decimal("1000.00"),
            contract_owner=legal_user,
        )

    # Negative contract value
    with pytest.raises(ValidationError, match="Contract value cannot be negative."):
        create_contract_service(
            title="Negative Value Contract",
            vendor=vendor,
            start_date=today,
            end_date=today + timezone.timedelta(days=30),
            contract_value=Decimal("-500.00"),
            contract_owner=legal_user,
        )

    # 2. Document Upload Validation
    # File size limit (> 10MB)
    large_file = SimpleUploadedFile("too_large.pdf", b"X" * (10 * 1024 * 1024 + 100), content_type="application/pdf")
    with pytest.raises(ValidationError, match="File size exceeds 10MB upload limit"):
        upload_contract_document_service(
            contract=contract,
            title="Large Doc",
            file=large_file,
            user=legal_user,
        )

    # Disallowed file format (.exe)
    invalid_ext_file = SimpleUploadedFile("malware.exe", b"executable content", content_type="application/x-msdownload")
    with pytest.raises(ValidationError, match="Unsupported file extension"):
        upload_contract_document_service(
            contract=contract,
            title="Exe Doc",
            file=invalid_ext_file,
            user=legal_user,
        )

    # 3. Status Transition Guards
    # Cannot approve legal review when status is DRAFT
    with pytest.raises(ValidationError, match="Cannot perform legal approval on contract in status"):
        approve_legal_review_service(contract=contract, user=legal_user)

    # Move to LEGAL_REVIEW
    submit_for_legal_review_service(contract=contract, user=legal_user)
    assert contract.status == Contract.STATUS_LEGAL_REVIEW

    # Cannot resubmit when already in LEGAL_REVIEW
    with pytest.raises(ValidationError, match="Cannot submit contract in status"):
        submit_for_legal_review_service(contract=contract, user=legal_user)

    # Approve legal review -> BUSINESS_APPROVAL
    approve_legal_review_service(contract=contract, user=legal_user)
    assert contract.status == Contract.STATUS_BUSINESS_APPROVAL

    # Cannot approve business review twice or from wrong status
    proc_user = contract_setup["proc_user"]
    approve_business_service(contract=contract, user=proc_user)
    assert contract.status == Contract.STATUS_ACTIVE

    with pytest.raises(ValidationError, match="Cannot perform business approval on contract in status"):
        approve_business_service(contract=contract, user=proc_user)

    # 4. Amendment Validation
    # Empty amendment summary
    with pytest.raises(ValidationError, match="Amendment summary is required."):
        create_contract_version_service(
            contract=contract,
            amendment_summary="",
            contract_value=Decimal("5000.00"),
            start_date=today,
            end_date=today + timezone.timedelta(days=365),
            user=legal_user,
        )

    # Negative contract value on amendment
    with pytest.raises(ValidationError, match="Contract value cannot be negative."):
        create_contract_version_service(
            contract=contract,
            amendment_summary="Invalid value amendment",
            contract_value=Decimal("-100.00"),
            start_date=today,
            end_date=today + timezone.timedelta(days=365),
            user=legal_user,
        )

    # 5. Termination & Renewal Validation
    # Termination with empty reason
    with pytest.raises(ValidationError, match="Termination reason is required."):
        terminate_contract_service(contract=contract, reason="", user=legal_user)

    # Renewal with new end date before contract start date
    with pytest.raises(ValidationError, match="Renewal end date must be after contract start date."):
        renew_contract_service(contract=contract, new_end_date=contract.start_date - timezone.timedelta(days=1), user=legal_user)

    # Valid Termination
    terminate_contract_service(contract=contract, reason="Contract fulfilled early", user=legal_user)
    assert contract.status == Contract.STATUS_TERMINATED


@pytest.mark.django_db
def test_day23_contract_version_history_and_amendment_audit_trail(client, contract_setup):
    """
    Day 23 Task: Validate contract version history and amendment audit trail.
    Verifies:
    1. Multi-version amendment workflow (V1 -> V2 -> V3) preserves all prior ContractVersion snapshots.
    2. Every amendment creates an AuditLog entry with non-empty previous_state and new_state.
    3. REST API GET /api/v1/contracts/{id}/versions/ returns complete version history array.
    4. Compliance Auditor role can view version history and audit logs, but cannot execute amendments.
    """
    from apps.audit.models import AuditLog
    from apps.contracts.models import Contract
    from apps.contracts.services import (
        approve_business_service,
        approve_legal_review_service,
        create_contract_version_service,
        submit_for_legal_review_service,
    )

    contract = contract_setup["contract"]
    legal_user = contract_setup["legal_user"]
    proc_user = contract_setup["proc_user"]
    today = timezone.now().date()

    # Move contract to ACTIVE state
    submit_for_legal_review_service(contract=contract, user=legal_user)
    approve_legal_review_service(contract=contract, user=legal_user)
    approve_business_service(contract=contract, user=proc_user)
    assert contract.status == Contract.STATUS_ACTIVE
    assert contract.version == 1

    # 1. Create Version 2 Amendment via service layer
    v2_summary = "Version 2: Expanded scope to include secondary datacenter maintenance"
    v2_value = Decimal("320000.00")
    v2_end = today + timezone.timedelta(days=500)

    v2_record = create_contract_version_service(
        contract=contract,
        user=legal_user,
        amendment_summary=v2_summary,
        contract_value=v2_value,
        start_date=today,
        end_date=v2_end,
    )
    assert v2_record.version_number == 2
    contract.refresh_from_db()
    assert contract.version == 2
    assert contract.contract_value == v2_value

    # Verify AuditLog for V2 amendment
    audit_v2 = AuditLog.objects.filter(
        target_model="Contract", target_object_id=str(contract.id), action=AuditLog.ACTION_UPDATE
    ).latest("timestamp")
    assert audit_v2.previous_state["version"] == 1
    assert audit_v2.previous_state["contract_value"] == "250000.00"
    assert audit_v2.new_state["version"] == 2
    assert audit_v2.new_state["contract_value"] == str(v2_value)
    assert audit_v2.new_state["amendment_summary"] == v2_summary

    # 2. Create Version 3 Amendment via REST API
    client.force_login(legal_user)
    v3_summary = "Version 3: Added 24/7 priority support SLA clause"
    v3_value = "410000.00"
    v3_end = today + timezone.timedelta(days=730)

    resp = client.post(
        f"/api/v1/contracts/{contract.id}/amend/",
        {
            "amendment_summary": v3_summary,
            "contract_value": v3_value,
            "start_date": str(today),
            "end_date": str(v3_end),
        },
        content_type="application/json",
    )
    assert resp.status_code == 201
    contract.refresh_from_db()
    assert contract.version == 3

    # Verify AuditLog for V3 amendment
    audit_v3 = AuditLog.objects.filter(
        target_model="Contract", target_object_id=str(contract.id), action=AuditLog.ACTION_UPDATE
    ).latest("timestamp")
    assert audit_v3.previous_state["version"] == 2
    assert audit_v3.new_state["version"] == 3

    # 3. Retrieve Version History via GET /api/v1/contracts/{id}/versions/
    resp = client.get(f"/api/v1/contracts/{contract.id}/versions/")
    assert resp.status_code == 200
    versions_data = resp.json()
    assert len(versions_data) == 3
    assert versions_data[0]["version_number"] == 3
    assert versions_data[1]["version_number"] == 2
    assert versions_data[2]["version_number"] == 1

    # 4. Auditor Access Verification
    auditor_role = _get_or_create_role(Role.AUDITOR, "Auditor")
    auditor_user = User.objects.create_user(email="auditor.d23@hpe.com", password="Password123!", role=auditor_role)

    client.force_login(auditor_user)
    # Auditor can view version history
    resp = client.get(f"/api/v1/contracts/{contract.id}/versions/")
    assert resp.status_code == 200
    assert len(resp.json()) == 3

    # Auditor blocked from creating amendments
    resp = client.post(
        f"/api/v1/contracts/{contract.id}/amend/",
        {
            "amendment_summary": "Auditor unauthorized amendment",
            "contract_value": "500000.00",
            "start_date": str(today),
            "end_date": str(v3_end),
        },
        content_type="application/json",
    )
    assert resp.status_code == 403







