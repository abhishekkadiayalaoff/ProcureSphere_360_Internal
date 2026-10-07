import csv
import io

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.contracts.models import Contract
from apps.invoices.models import MatchException
from apps.orders.models import PurchaseOrder
from apps.receipts.models import ReceiptLine
from apps.requisitions.models import PurchaseRequisition
from apps.scorecards.models import VendorScorecard
from apps.sourcing.models import SourcingEvent

from .models import ExportJob


def get_pr_aging_report():
    """1. PR aging and approval-bottleneck report"""
    prs = PurchaseRequisition.objects.select_related("requester", "department", "cost_center").all()
    now = timezone.now()
    report_data = []
    for pr in prs:
        age_days = (now - pr.created_at).days
        report_data.append(
            {
                "pr_number": pr.pr_number,
                "title": pr.title,
                "department": pr.department.name if pr.department else "N/A",
                "cost_center": pr.cost_center.code if pr.cost_center else "N/A",
                "status": pr.status,
                "total_amount": float(pr.total_amount),
                "created_at": pr.created_at.strftime("%Y-%m-%d"),
                "age_days": age_days,
            }
        )
    return report_data


def get_spend_analytics_report():
    """2. Spend by vendor / category / department / cost center / period"""
    from apps.invoices.models import SupplierInvoice

    invoices = (
        SupplierInvoice.objects.select_related(
            "vendor", "vendor__category", "po", "po__cost_center", "po__requisition__department"
        )
        .exclude(status="REJECTED")
        .order_by("-invoice_date")
    )

    report_data = []
    for inv in invoices:
        po = inv.po
        dept_name = (
            po.requisition.department.name
            if po and po.requisition and po.requisition.department
            else "N/A"
        )
        cc_code = po.cost_center.code if po and po.cost_center else "N/A"
        cat_name = inv.vendor.category.name if inv.vendor.category else "Uncategorized"
        period_str = inv.invoice_date.strftime("%Y-%m")

        report_data.append(
            {
                "vendor_name": inv.vendor.legal_name,
                "vendor_category": cat_name,
                "department": dept_name,
                "cost_center": cc_code,
                "period": period_str,
                "invoice_number": inv.invoice_number,
                "po_number": po.po_number if po else "N/A",
                "status": inv.get_status_display(),
                "actual_spend": float(inv.total_amount),
            }
        )

    return report_data


def get_sourcing_cycle_time_report():
    """3. Sourcing cycle time and bid participation"""
    events = SourcingEvent.objects.prefetch_related("bids", "invitations").all()
    report_data = []
    for e in events:
        bid_count = e.bids.count()
        invite_count = e.invitations.count()
        report_data.append(
            {
                "event_number": e.event_number,
                "title": e.title,
                "event_type": e.event_type,
                "status": e.status,
                "invited_vendors": invite_count,
                "submitted_bids": bid_count,
                "start_date": str(e.start_date),
                "end_date": str(e.end_date),
            }
        )
    return report_data


def get_po_status_report():
    """4. PO open / partial / closed status"""
    pos = PurchaseOrder.objects.select_related("vendor", "cost_center").all()
    report_data = []
    for po in pos:
        report_data.append(
            {
                "po_number": po.po_number,
                "version": po.version,
                "vendor": po.vendor.legal_name,
                "cost_center": po.cost_center.code,
                "status": po.status,
                "total_amount": float(po.total_amount),
                "acknowledged_at": str(po.acknowledged_at) if po.acknowledged_at else None,
            }
        )
    return report_data


def get_receipt_rejection_report():
    """5. Receipt / rejection and delivery performance"""
    receipt_lines = ReceiptLine.objects.select_related("receipt__po__vendor", "po_line").all()
    report_data = []
    for rl in receipt_lines:
        report_data.append(
            {
                "grn_number": rl.receipt.grn_number,
                "po_number": rl.receipt.po.po_number,
                "vendor": rl.receipt.po.vendor.legal_name,
                "received_date": rl.receipt.received_date.strftime("%Y-%m-%d"),
                "qty_received": float(rl.quantity_received),
                "qty_accepted": float(rl.quantity_accepted),
                "qty_rejected": float(rl.quantity_rejected),
            }
        )
    return report_data


def get_invoice_exception_aging_report():
    """6. Invoice match-exception aging"""
    exceptions = MatchException.objects.select_related("invoice__vendor", "resolved_by").all()
    now = timezone.now()
    report_data = []
    for exc in exceptions:
        age_days = (now - exc.created_at).days
        report_data.append(
            {
                "invoice_number": exc.invoice.invoice_number,
                "vendor": exc.invoice.vendor.legal_name,
                "exception_type": exc.exception_type,
                "status": exc.status,
                "variance_amount": float(exc.variance_amount),
                "age_days": age_days,
                "resolved_by": exc.resolved_by.email if exc.resolved_by else None,
            }
        )
    return report_data


def get_contract_expiry_report():
    """7. Contract expiry / renewal / obligation"""
    contracts = Contract.objects.select_related("vendor").all()
    now = timezone.now().date()
    report_data = []
    for c in contracts:
        days_to_expiry = (c.end_date - now).days if c.end_date else 0
        report_data.append(
            {
                "contract_number": c.contract_number,
                "title": c.title,
                "vendor": c.vendor.legal_name,
                "status": c.status,
                "total_value": float(c.contract_value),
                "end_date": str(c.end_date),
                "days_to_expiry": days_to_expiry,
            }
        )
    return report_data


def _score(value):
    """Scorecard indicators are NULL when no transactional data exists."""
    return None if value is None else float(value)


def get_supplier_performance_report():
    """8. Supplier performance scorecard and trend"""
    scorecards = VendorScorecard.objects.select_related("vendor", "evaluated_by").all()
    report_data = []
    for sc in scorecards:
        report_data.append(
            {
                "vendor": sc.vendor.legal_name,
                "period": sc.evaluation_period,
                "delivery_score": _score(sc.delivery_score),
                "quality_score": _score(sc.quality_score),
                "price_score": _score(sc.price_score),
                "responsiveness_score": _score(sc.responsiveness_score),
                "compliance_score": _score(sc.compliance_score),
                "sla_score": _score(sc.sla_score),
                "composite_score": _score(sc.composite_score),
                "evaluated_by": sc.evaluated_by.email,
            }
        )
    return report_data


def get_audit_log_report():
    """9. User / approval audit export with filters and immutable references"""
    logs = AuditLog.objects.select_related("actor").all()[:200]
    report_data = []
    for log in logs:
        report_data.append(
            {
                "audit_id": str(log.id),
                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "actor": log.actor.email if log.actor else "System",
                "action": log.action,
                "target_model": log.target_model,
                "target_object_id": log.target_object_id,
            }
        )
    return report_data


REPORT_DISPATCHER = {
    "pr_aging": get_pr_aging_report,
    "spend_analytics": get_spend_analytics_report,
    "sourcing_cycle_time": get_sourcing_cycle_time_report,
    "po_status": get_po_status_report,
    "receipt_rejection": get_receipt_rejection_report,
    "invoice_exception_aging": get_invoice_exception_aging_report,
    "contract_expiry": get_contract_expiry_report,
    "supplier_performance": get_supplier_performance_report,
    "audit_log": get_audit_log_report,
}


def generate_export_job_service(export_job_id: int) -> ExportJob:
    """
    Processes an ExportJob, generates CSV, XLSX, or PDF file, attaches result file, and logs audit event.
    """
    job = ExportJob.objects.get(pk=export_job_id)
    job.status = ExportJob.STATUS_PROCESSING
    job.save(update_fields=["status", "updated_at"])

    try:
        report_fn = REPORT_DISPATCHER.get(job.report_type, get_audit_log_report)
        data = report_fn()

        if not data:
            # Fallback for empty data
            fieldnames = ["Message"]
            data = [{"Message": "No data available for export."}]
        else:
            fieldnames = list(data[0].keys())

        if job.export_format == "CSV":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
            filename = f"{job.report_type}_export_{job.id}.csv"
            job.result_file.save(
                filename, ContentFile(output.getvalue().encode("utf-8")), save=False
            )

        elif job.export_format == "XLSX":
            from io import BytesIO

            import openpyxl

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report Data"
            ws.append(fieldnames)
            for row in data:
                ws.append([str(row.get(f, "")) for f in fieldnames])

            output = BytesIO()
            wb.save(output)
            filename = f"{job.report_type}_export_{job.id}.xlsx"
            job.result_file.save(filename, ContentFile(output.getvalue()), save=False)

        elif job.export_format == "PDF":
            from io import BytesIO

            from reportlab.lib import colors
            from reportlab.lib.pagesizes import landscape, letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=landscape(letter))

            # Prepare table data
            table_data = [fieldnames]
            for row in data:
                table_data.append([str(row.get(f, "")) for f in fieldnames])

            t = Table(table_data)
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ]
                )
            )

            elements = [t]
            doc.build(elements)

            filename = f"{job.report_type}_export_{job.id}.pdf"
            job.result_file.save(filename, ContentFile(output.getvalue()), save=False)

        job.status = ExportJob.STATUS_COMPLETED
        job.save(update_fields=["status", "result_file", "updated_at"])

        AuditLog.objects.create(
            actor=job.requested_by,
            action=AuditLog.ACTION_EXPORT,
            target_model="ExportJob",
            target_object_id=str(job.id),
            new_state={
                "report_type": job.report_type,
                "format": job.export_format,
                "record_count": len(data),
            },
        )
    except Exception as e:
        job.status = ExportJob.STATUS_FAILED
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise e

    return job
