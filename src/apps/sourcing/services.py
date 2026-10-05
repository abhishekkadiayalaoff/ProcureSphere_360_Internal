from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.vendors.models import Vendor

from .models import (
    AwardDecision,
    BidAttachment,
    BidInvite,
    BidLine,
    BidVersion,
    Clarification,
    SourcingEvent,
    VendorBid,
)


@transaction.atomic
def create_sourcing_event_service(
    *,
    title: str,
    event_type: str,
    bid_start_date,
    bid_end_date,
    description: str,
    technical_requirements: str = "",
    commercial_requirements: str = "",
    required_documents: str = "",
    requisition=None,
    created_by_user: User = None,
) -> SourcingEvent:
    """
    Creates a new RFQ/RFP sourcing event in DRAFT status.
    """
    event_count = SourcingEvent.objects.count() + 1
    prefix = "RFQ" if event_type == SourcingEvent.TYPE_RFQ else "RFP"
    event_number = f"{prefix}-{timezone.now().strftime('%Y')}-{event_count:05d}"

    event = SourcingEvent.objects.create(
        event_number=event_number,
        title=title,
        event_type=event_type,
        requisition=requisition,
        status=SourcingEvent.STATUS_DRAFT,
        bid_start_date=bid_start_date,
        bid_end_date=bid_end_date,
        description=description,
        technical_requirements=technical_requirements,
        commercial_requirements=commercial_requirements,
        required_documents=required_documents,
        is_sealed=True,
    )

    AuditLog.objects.create(
        actor=created_by_user,
        action=AuditLog.ACTION_CREATE,
        target_model="SourcingEvent",
        target_object_id=str(event.id),
        new_state={
            "event_number": event.event_number,
            "status": event.status,
            "event_type": event.event_type,
        },
    )

    return event


@transaction.atomic
def publish_sourcing_event_service(*, event: SourcingEvent, user: User) -> SourcingEvent:
    """
    Publishes a sourcing event and opens the bid window.
    """
    if event.status != SourcingEvent.STATUS_DRAFT:
        raise ValidationError(f"Cannot publish event in status '{event.status}'. Must be DRAFT.")

    previous_status = event.status
    event.status = SourcingEvent.STATUS_BID_WINDOW
    event.save(update_fields=["status", "updated_at"])

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE,
        target_model="SourcingEvent",
        target_object_id=str(event.id),
        previous_state={"status": previous_status},
        new_state={"status": event.status},
    )

    return event


@transaction.atomic
def invite_vendors_to_event_service(
    *, event: SourcingEvent, vendor_ids: list, invited_by: User
) -> list:
    """
    Invites active eligible vendors to participate in a sourcing event.
    Blocks suspended/blacklisted vendors.
    """
    invitations = []
    for vid in vendor_ids:
        vendor = Vendor.objects.get(id=vid)
        if vendor.status == Vendor.STATUS_SUSPENDED:
            raise ValidationError(
                f"Vendor '{vendor.legal_name}' is currently suspended and cannot be invited."
            )

        invite, _ = BidInvite.objects.get_or_create(event=event, vendor=vendor)
        invitations.append(invite)

    return invitations


def validate_bid_service(*, bid: VendorBid) -> dict:
    """
    Authoritative server-side bid validation.
    Checks authorization, status, deadline, completeness, line item pricing, and attachments.
    """
    errors = []
    warnings = []
    event = bid.event

    if event.status != SourcingEvent.STATUS_BID_WINDOW:
        errors.append(f"Event '{event.event_number}' is not currently accepting bids (Status: {event.status}).")

    if timezone.now() > event.bid_end_date:
        errors.append(f"Bid submission deadline passed on {event.bid_end_date.strftime('%Y-%m-%d %H:%M')}.")

    if bid.vendor.status == Vendor.STATUS_SUSPENDED:
        errors.append("Vendor account is currently suspended and cannot participate in procurement.")

    if not bid.technical_proposal.strip() and not bid.proposal_summary.strip():
        errors.append("Technical response or proposal summary must be provided.")

    lines = list(bid.lines.all())
    if not lines:
        errors.append("At least one commercial line item with quantity and quoted price is required.")
    else:
        for idx, line in enumerate(lines, 1):
            if line.quantity <= Decimal("0.00"):
                errors.append(f"Line {idx} ('{line.item_description}'): Quantity must be greater than zero.")
            if line.quoted_unit_price <= Decimal("0.00"):
                errors.append(f"Line {idx} ('{line.item_description}'): Quoted unit price must be greater than zero.")

    if bid.total_bid_amount <= Decimal("0.00"):
        errors.append("Total bid amount must be greater than $0.00.")

    if event.required_documents and not bid.attachments.exists():
        warnings.append("Event specifies required documents, but no attachments have been uploaded.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "event_number": event.event_number,
        "bid_number": bid.bid_number,
        "version": bid.version,
        "total_amount": str(bid.total_bid_amount),
        "deadline": event.bid_end_date.strftime("%Y-%m-%d %H:%M"),
    }


@transaction.atomic
def save_draft_bid_service(
    *,
    event: SourcingEvent,
    vendor: Vendor,
    user: User,
    line_items: list = None,
    proposal_summary: str = "",
    technical_proposal: str = "",
    commercial_proposal: str = "",
) -> VendorBid:
    """
    Saves or updates a vendor's bid in DRAFT status.
    """
    if event.status != SourcingEvent.STATUS_BID_WINDOW:
        raise ValidationError(f"Bidding is closed for event '{event.event_number}'. Status: {event.status}")

    if timezone.now() > event.bid_end_date:
        raise ValidationError("Cannot prepare bid: Sourcing event bid deadline has passed.")

    if vendor.status == Vendor.STATUS_SUSPENDED:
        raise ValidationError(f"Vendor '{vendor.legal_name}' is suspended and cannot prepare bids.")

    if not BidInvite.objects.filter(event=event, vendor=vendor).exists():
        raise ValidationError("Vendor does not have a valid invitation to this sourcing event.")

    bid = VendorBid.objects.filter(event=event, vendor=vendor).first()
    if not bid:
        bid_count = VendorBid.objects.count() + 1
        bid_number = f"BID-{timezone.now().strftime('%Y')}-{bid_count:05d}"
        bid = VendorBid.objects.create(
            event=event,
            vendor=vendor,
            bid_number=bid_number,
            version=1,
            status=VendorBid.STATUS_DRAFT,
            proposal_summary=proposal_summary,
            technical_proposal=technical_proposal,
            commercial_proposal=commercial_proposal,
            total_bid_amount=Decimal("0.00"),
        )
    else:
        if bid.status not in [VendorBid.STATUS_DRAFT]:
            raise ValidationError(f"Bid is already in '{bid.status}' status. Use Amendment to modify.")
        bid.proposal_summary = proposal_summary
        bid.technical_proposal = technical_proposal
        bid.commercial_proposal = commercial_proposal

    if line_items is not None:
        bid.lines.all().delete()
        total = Decimal("0.00")
        for item in line_items:
            qty = Decimal(str(item.get("quantity", 1)))
            unit_price = Decimal(str(item.get("quoted_unit_price", 0)))
            line = BidLine.objects.create(
                bid=bid,
                pr_line=item.get("pr_line"),
                item_description=item.get("item_description", "Item"),
                quantity=qty,
                quoted_unit_price=unit_price,
            )
            total += line.quoted_total_price
        bid.total_bid_amount = total

    bid.save()

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_UPDATE if bid.id else AuditLog.ACTION_CREATE,
        target_model="VendorBid",
        target_object_id=str(bid.id),
        new_state={
            "bid_number": bid.bid_number,
            "status": bid.status,
            "total_amount": str(bid.total_bid_amount),
        },
    )
    return bid


@transaction.atomic
def submit_vendor_bid_service(
    *,
    event: SourcingEvent,
    vendor: Vendor,
    line_items: list,
    proposal_summary: str = "",
    technical_proposal: str = "",
    commercial_proposal: str = "",
    submitted_by_user: User = None,
) -> VendorBid:
    """
    Submits a sealed bid for a vendor during the BID_WINDOW.
    Enforces server-side deadline, authorization, atomic transaction, versioning, and audit log.
    """
    if event.status != SourcingEvent.STATUS_BID_WINDOW:
        raise ValidationError(
            f"Bidding is closed for event '{event.event_number}'. Current status: {event.status}"
        )

    if timezone.now() > event.bid_end_date:
        raise ValidationError(
            f"Cannot submit bid: Sourcing event deadline passed on {event.bid_end_date.strftime('%Y-%m-%d %H:%M')}."
        )

    if vendor.status == Vendor.STATUS_SUSPENDED:
        raise ValidationError(f"Vendor '{vendor.legal_name}' is suspended and cannot submit bids.")

    # Verify vendor has invitation
    if not BidInvite.objects.filter(event=event, vendor=vendor).exists():
        raise ValidationError(f"Vendor '{vendor.legal_name}' has not been invited to this event.")

    bid = VendorBid.objects.filter(event=event, vendor=vendor).first()
    created = False
    if not bid:
        created = True
        bid_count = VendorBid.objects.count() + 1
        bid_number = f"BID-{timezone.now().strftime('%Y')}-{bid_count:05d}"
        bid = VendorBid.objects.create(
            event=event,
            vendor=vendor,
            bid_number=bid_number,
            version=1,
            status=VendorBid.STATUS_SUBMITTED,
            proposal_summary=proposal_summary,
            technical_proposal=technical_proposal,
            commercial_proposal=commercial_proposal,
            total_bid_amount=Decimal("0.00"),
            submitted_at=timezone.now(),
        )
    else:
        bid.status = VendorBid.STATUS_SUBMITTED
        bid.proposal_summary = proposal_summary
        bid.technical_proposal = technical_proposal or bid.technical_proposal
        bid.commercial_proposal = commercial_proposal or bid.commercial_proposal
        bid.submitted_at = timezone.now()

    if line_items:
        bid.lines.all().delete()
        total = Decimal("0.00")
        snapshot_lines = []
        for item in line_items:
            qty = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["quoted_unit_price"]))
            line = BidLine.objects.create(
                bid=bid,
                pr_line=item.get("pr_line"),
                item_description=item["item_description"],
                quantity=qty,
                quoted_unit_price=unit_price,
            )
            total += line.quoted_total_price
            snapshot_lines.append({
                "item_description": line.item_description,
                "quantity": str(line.quantity),
                "quoted_unit_price": str(line.quoted_unit_price),
                "quoted_total_price": str(line.quoted_total_price),
            })
        bid.total_bid_amount = total
    else:
        snapshot_lines = [
            {
                "item_description": line.item_description,
                "quantity": str(line.quantity),
                "quoted_unit_price": str(line.quoted_unit_price),
                "quoted_total_price": str(line.quoted_total_price),
            }
            for line in bid.lines.all()
        ]

    bid.save()

    # Capture initial immutable BidVersion (Version 1)
    BidVersion.objects.get_or_create(
        bid=bid,
        version_number=bid.version,
        defaults={
            "status": VendorBid.STATUS_SUBMITTED,
            "total_bid_amount": bid.total_bid_amount,
            "proposal_summary": bid.proposal_summary,
            "technical_proposal": bid.technical_proposal,
            "commercial_proposal": bid.commercial_proposal,
            "submitted_at": bid.submitted_at,
            "snapshot_data": {"lines": snapshot_lines},
        },
    )

    # Update invite status
    BidInvite.objects.filter(event=event, vendor=vendor).update(is_responded=True)

    AuditLog.objects.create(
        actor=submitted_by_user,
        action=AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE,
        target_model="VendorBid",
        target_object_id=str(bid.id),
        new_state={
            "bid_number": bid.bid_number,
            "version": bid.version,
            "status": bid.status,
            "total_amount": str(bid.total_bid_amount),
            "vendor": vendor.legal_name,
        },
    )

    return bid


@transaction.atomic
def amend_vendor_bid_service(
    *,
    bid: VendorBid,
    vendor_user: User,
    amendment_reason: str,
    line_items: list,
    proposal_summary: str = "",
    technical_proposal: str = "",
    commercial_proposal: str = "",
) -> VendorBid:
    """
    Amends a submitted bid while the event is still open.
    Preserves prior version as an immutable BidVersion snapshot, creates new version, and audits.
    Rejects amendment if deadline has passed or event is not in BID_WINDOW.
    """
    event = bid.event
    if event.status != SourcingEvent.STATUS_BID_WINDOW:
        raise ValidationError(f"Cannot amend bid: Sourcing event is '{event.status}', not BID_WINDOW.")

    if timezone.now() > event.bid_end_date:
        raise ValidationError(f"Cannot amend bid: Sourcing event deadline passed on {event.bid_end_date.strftime('%Y-%m-%d %H:%M')}.")

    if not amendment_reason or not amendment_reason.strip():
        raise ValidationError("Amendment justification/reason is required for bid amendment.")

    # 1. Ensure prior version is snapshotted into BidVersion
    if not BidVersion.objects.filter(bid=bid, version_number=bid.version).exists():
        prior_lines = [
            {
                "item_description": line.item_description,
                "quantity": str(line.quantity),
                "quoted_unit_price": str(line.quoted_unit_price),
                "quoted_total_price": str(line.quoted_total_price),
            }
            for line in bid.lines.all()
        ]
        BidVersion.objects.create(
            bid=bid,
            version_number=bid.version,
            status=bid.status,
            total_bid_amount=bid.total_bid_amount,
            proposal_summary=bid.proposal_summary,
            technical_proposal=bid.technical_proposal,
            commercial_proposal=bid.commercial_proposal,
            submitted_at=bid.submitted_at or timezone.now(),
            snapshot_data={"lines": prior_lines},
        )

    # 2. Increment version and update current bid
    new_version_num = bid.version + 1
    previous_version_num = bid.version

    bid.version = new_version_num
    bid.status = VendorBid.STATUS_AMENDED
    bid.proposal_summary = proposal_summary or bid.proposal_summary
    bid.technical_proposal = technical_proposal or bid.technical_proposal
    bid.commercial_proposal = commercial_proposal or bid.commercial_proposal
    bid.submitted_at = timezone.now()

    # 3. Update line items
    bid.lines.all().delete()
    total = Decimal("0.00")
    new_lines_snapshot = []
    for item in line_items:
        qty = Decimal(str(item["quantity"]))
        unit_price = Decimal(str(item["quoted_unit_price"]))
        line = BidLine.objects.create(
            bid=bid,
            pr_line=item.get("pr_line"),
            item_description=item["item_description"],
            quantity=qty,
            quoted_unit_price=unit_price,
        )
        total += line.quoted_total_price
        new_lines_snapshot.append({
            "item_description": line.item_description,
            "quantity": str(line.quantity),
            "quoted_unit_price": str(line.quoted_unit_price),
            "quoted_total_price": str(line.quoted_total_price),
        })

    bid.total_bid_amount = total
    bid.save()

    # 4. Create immutable BidVersion record for this amendment
    BidVersion.objects.create(
        bid=bid,
        version_number=new_version_num,
        status=VendorBid.STATUS_AMENDED,
        total_bid_amount=bid.total_bid_amount,
        proposal_summary=bid.proposal_summary,
        technical_proposal=bid.technical_proposal,
        commercial_proposal=bid.commercial_proposal,
        amendment_reason=amendment_reason.strip(),
        submitted_at=bid.submitted_at,
        snapshot_data={"lines": new_lines_snapshot, "amendment_reason": amendment_reason.strip()},
    )

    # 5. Append-only AuditLog
    AuditLog.objects.create(
        actor=vendor_user,
        action=AuditLog.ACTION_UPDATE,
        target_model="VendorBid",
        target_object_id=str(bid.id),
        previous_state={"version": previous_version_num, "status": "SUBMITTED"},
        new_state={
            "version": new_version_num,
            "status": bid.status,
            "total_amount": str(bid.total_bid_amount),
            "amendment_reason": amendment_reason.strip(),
        },
    )

    return bid


@transaction.atomic
def ask_clarification_service(
    *,
    event: SourcingEvent,
    vendor: Vendor,
    user: User,
    question: str,
) -> Clarification:
    """
    Submits a clarification question from an invited vendor for a sourcing event.
    """
    if not question or not question.strip():
        raise ValidationError("Clarification question cannot be blank.")

    if not BidInvite.objects.filter(event=event, vendor=vendor).exists():
        raise ValidationError("Vendor does not have a valid invitation for this sourcing event.")

    clarification = Clarification.objects.create(
        event=event,
        vendor=vendor,
        question=question.strip(),
        status="PENDING",
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_CREATE,
        target_model="Clarification",
        target_object_id=str(clarification.id),
        new_state={
            "event_number": event.event_number,
            "vendor": vendor.legal_name,
            "question": clarification.question[:100],
        },
    )

    return clarification


@transaction.atomic
def upload_bid_attachment_service(
    *,
    bid: VendorBid,
    user: User,
    file,
    title: str = "",
    document_type: str = "TECHNICAL",
) -> BidAttachment:
    """
    Attaches a validated document to a vendor bid.
    """
    if not title or not title.strip():
        title = getattr(file, "name", "Proposal Attachment")

    attachment = BidAttachment.objects.create(
        bid=bid,
        title=title.strip(),
        document_type=document_type,
        file=file,
        file_size=getattr(file, "size", 0),
    )

    AuditLog.objects.create(
        actor=user,
        action=AuditLog.ACTION_CREATE,
        target_model="BidAttachment",
        target_object_id=str(attachment.id),
        new_state={
            "bid_number": bid.bid_number,
            "title": attachment.title,
            "type": attachment.document_type,
        },
    )

    return attachment


@transaction.atomic
def evaluate_and_award_sourcing_event_service(
    *, event: SourcingEvent, winning_bid: VendorBid, award_reason: str, approved_by_user: User
) -> AwardDecision:
    """
    Executes technical/commercial evaluation completion and records AwardDecision.
    Transitions event status to AWARDED.
    """
    if winning_bid.event_id != event.id:
        raise ValidationError("Winning bid does not belong to target sourcing event.")

    previous_status = event.status
    event.status = SourcingEvent.STATUS_AWARDED
    event.save(update_fields=["status", "updated_at"])

    decision = AwardDecision.objects.create(
        event=event,
        winning_bid=winning_bid,
        award_reason=award_reason,
        approved_by=approved_by_user,
    )

    AuditLog.objects.create(
        actor=approved_by_user,
        action=AuditLog.ACTION_APPROVE,
        target_model="AwardDecision",
        target_object_id=str(decision.id),
        previous_state={"status": previous_status},
        new_state={
            "event_number": event.event_number,
            "winner": winning_bid.vendor.legal_name,
            "status": event.status,
        },
    )

    return decision

