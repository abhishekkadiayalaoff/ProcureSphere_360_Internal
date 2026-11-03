from django.db import migrations


def repair_corrupted_admin_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Role = apps.get_model("accounts", "Role")

    requester_role = Role.objects.filter(code="REQUESTER").first()
    if not requester_role:
        return

    # Specifically repair users corrupted by previous cross-org super admin creation attempts
    target_emails = [
        "shaiksamreen7981@gmail.com",
        "sameerbasha.0809@gmail.com",
    ]

    for email in target_emails:
        u = User.objects.filter(email__iexact=email).first()
        if u:
            # If user has a department or cost center or was mistakenly given super admin
            if u.role and u.role.code == "SUPER_ADMIN":
                u.role = requester_role
            u.must_change_password = False
            u.is_staff = False
            u.is_superuser = False
            u.save(update_fields=["role", "must_change_password", "is_staff", "is_superuser"])

    # General guard: In ProcureSphere 360, Super Admin / Admin roles are organization-wide with NO department.
    # Any user linked to a department or cost center with a SUPER_ADMIN role was corrupted.
    for user in User.objects.filter(role__code="SUPER_ADMIN").exclude(is_superuser=True):
        if user.department_id is not None or user.cost_center_id is not None:
            user.role = requester_role
            user.must_change_password = False
            user.is_staff = False
            user.is_superuser = False
            user.save(update_fields=["role", "must_change_password", "is_staff", "is_superuser"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_auto_link_tenant_users_to_org"),
    ]

    operations = [
        migrations.RunPython(repair_corrupted_admin_roles, noop),
    ]
