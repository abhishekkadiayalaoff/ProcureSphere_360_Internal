from django.db import migrations


def repair_corrupted_admin_roles(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Role = apps.get_model("accounts", "Role")

    requester_role = Role.objects.filter(code="REQUESTER").first()
    finance_role = Role.objects.filter(code="FINANCE_AP").first()

    # Repair sameerbasha.0809@gmail.com -> Finance dashboard mail (Finance / AP Specialist)
    sameer = User.objects.filter(email__iexact="sameerbasha.0809@gmail.com").first()
    if sameer:
        if finance_role:
            sameer.role = finance_role
        sameer.department = None
        sameer.cost_center = None
        sameer.first_name = ""
        sameer.last_name = ""
        sameer.must_change_password = False
        sameer.is_staff = False
        sameer.is_superuser = False
        sameer.save(update_fields=[
            "role", "department", "cost_center", "first_name", "last_name",
            "must_change_password", "is_staff", "is_superuser"
        ])

    # Repair shaiksamreen7981@gmail.com -> Requester
    samreen = User.objects.filter(email__iexact="shaiksamreen7981@gmail.com").first()
    if samreen:
        if requester_role:
            samreen.role = requester_role
        samreen.first_name = ""
        samreen.last_name = ""
        samreen.must_change_password = False
        samreen.is_staff = False
        samreen.is_superuser = False
        samreen.save(update_fields=[
            "role", "first_name", "last_name",
            "must_change_password", "is_staff", "is_superuser"
        ])

    # General cleanup: Any non-requester role should not have department/cost-center, and clear test names
    if requester_role:
        for user in User.objects.filter(role__code="SUPER_ADMIN").exclude(is_superuser=True):
            if user.department_id is not None or user.cost_center_id is not None:
                user.role = requester_role
                user.first_name = ""
                user.last_name = ""
                user.must_change_password = False
                user.is_staff = False
                user.is_superuser = False
                user.save(update_fields=["role", "first_name", "last_name", "must_change_password", "is_staff", "is_superuser"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_auto_link_tenant_users_to_org"),
    ]

    operations = [
        migrations.RunPython(repair_corrupted_admin_roles, noop),
    ]
