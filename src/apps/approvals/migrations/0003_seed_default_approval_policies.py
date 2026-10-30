from decimal import Decimal
from django.db import migrations


def seed_default_policies(apps, schema_editor):
    ApprovalPolicy = apps.get_model("approvals", "ApprovalPolicy")
    ApprovalStep = apps.get_model("approvals", "ApprovalStep")
    Role = apps.get_model("accounts", "Role")

    dept_approver_role, _ = Role.objects.get_or_create(
        code="DEPT_APPROVER", defaults={"name": "Department Approver"}
    )
    proc_mgr_role, _ = Role.objects.get_or_create(
        code="PROC_MGR", defaults={"name": "Procurement Manager"}
    )

    # 1. Global PR Approval Policy (covers $0.00 and above for all departments without custom policy)
    pr_policy, created = ApprovalPolicy.objects.get_or_create(
        module="PR",
        department=None,
        cost_center=None,
        defaults={
            "name": "Standard PR Approval — Global",
            "min_amount": Decimal("0.00"),
            "max_amount": None,
            "is_active": True,
        },
    )
    if created or not pr_policy.steps.exists():
        ApprovalStep.objects.get_or_create(
            policy=pr_policy,
            step_number=1,
            defaults={
                "approver_role": dept_approver_role,
                "description": "Department Manager Approval",
            },
        )
        ApprovalStep.objects.get_or_create(
            policy=pr_policy,
            step_number=2,
            defaults={
                "approver_role": proc_mgr_role,
                "description": "Procurement Manager Approval",
            },
        )

    # 2. Global PO Amendment Policy
    po_amend_policy, created = ApprovalPolicy.objects.get_or_create(
        module="PO_AMENDMENT",
        department=None,
        cost_center=None,
        defaults={
            "name": "PO Amendment Approval — Global",
            "min_amount": Decimal("0.00"),
            "max_amount": None,
            "is_active": True,
        },
    )
    if created or not po_amend_policy.steps.exists():
        ApprovalStep.objects.get_or_create(
            policy=po_amend_policy,
            step_number=1,
            defaults={
                "approver_role": proc_mgr_role,
                "description": "Procurement Manager Approval",
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("approvals", "0002_approvalpolicy_cost_center_module_choices"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_default_policies, noop),
    ]
