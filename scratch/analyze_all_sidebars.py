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
    print("=" * 80)
    print(f"SIDEBAR: {name} ({path})")
    print("=" * 80)
    if not os.path.exists(path):
        print("FILE NOT FOUND!")
        continue
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Find all nav links or a tags inside nav / aside
    # Regex for <a> with an <i> tag
    pattern = re.compile(r'<a\s+[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>')
    for m in pattern.finditer(text):
        href = m.group(1)
        inner = m.group(2)
        # Check if it has an icon
        icon_match = re.search(r'<i\s+class="([^"]+)"(?:\s+style="([^"]+)")?', inner)
        if icon_match:
            icon_cls = icon_match.group(1)
            icon_style = icon_match.group(2) or ""
            # Clean text
            clean_text = " ".join(re.sub(r'<[^>]+>', ' ', inner).split())
            print(f"  {href:35} | {icon_cls:45} | {icon_style:18} | {clean_text}")


