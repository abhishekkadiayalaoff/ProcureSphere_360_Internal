from apps.accounts.models import Role


def layout_context(request):
    """
    Context processor to provide dynamic base_layout template name depending on current user role.
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        role_code = getattr(user, "role_code", None) or (
            user.role.code if hasattr(user, "role") and user.role else None
        )
        if role_code == Role.LEGAL_MGR or role_code == "LEGAL_MGR":
            return {"base_layout": "layouts/legal_base.html"}
        elif role_code == Role.SUPER_ADMIN or role_code == "SUPER_ADMIN":
            return {"base_layout": "layouts/superadmin_base.html"}
        elif role_code == Role.FINANCE_AP or role_code == "FINANCE_AP":
            return {"base_layout": "layouts/finance_base.html"}
        elif role_code == Role.REQUESTER or role_code == "REQUESTER":
            return {"base_layout": "layouts/requester_base.html"}
        elif (
            hasattr(Role, "VENDOR_USER")
            and (role_code == Role.VENDOR_USER or role_code == "VENDOR_USER")
        ) or role_code == "VENDOR":
            return {"base_layout": "layouts/vendor_base.html"}
    return {"base_layout": "base.html"}
