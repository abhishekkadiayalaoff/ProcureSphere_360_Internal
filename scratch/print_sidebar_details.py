import re
import os

sidebar_files = {
    "Vendor (Reference)": "templates/layouts/vendor_base.html",
    "Super Admin": "templates/layouts/superadmin_base.html",
    "Procurement Manager": "templates/manager/base_manager.html",
    "Procurement Executive": "templates/partials/proc_exec_sidebar.html",
    "Requester": "templates/layouts/requester_base.html",
    "Approver": "templates/layouts/approver_base.html",
    "Stores": "templates/layouts/stores_base.html",
    "Legal": "templates/layouts/legal_base.html",
    "Auditor": "templates/audit/base_auditor.html",
}

for name, path in sidebar_files.items():
    print(f"\n### {name} (`{path}`)")
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Match nav links
    pattern = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*class="([^"]*nav[^"]*)"[^>]*>([\s\S]*?)</a>')
    matches = list(pattern.finditer(text))
    if not matches:
        # Fallback to general a with nav-link or vendor-navlink or sa-navlink or manager-nav-link
        pattern = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>')
        for m in pattern.finditer(text):
            inner = m.group(2)
            if "nav-icon" in inner or "fa-solid" in inner:
                if "/logout/" not in m.group(1) and "navbar-brand" not in m.group(0):
                    matches.append(m)

    for m in matches:
        href = m.group(1)
        inner = m.group(m.lastindex)
        icon_match = re.search(r'<i\s+class="([^"]+)"(?:\s+style="([^"]+)")?', inner)
        if icon_match:
            icon_cls = icon_match.group(1)
            icon_style = icon_match.group(2) or ""
            clean_text = " ".join(re.sub(r'<[^>]+>', ' ', inner).split())
            if "/logout" not in href and "navbar-brand" not in icon_cls:
                print(f"- **{clean_text}** (`{href}`): `{icon_cls}` {f'style=\"{icon_style}\"' if icon_style else ''}")

