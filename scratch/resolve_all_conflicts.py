import re
import os

def resolve_policy_form():
    path = "templates/pages/dashboards/superadmin/policy_form.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Conflict 1
    pattern = re.compile(r"<{7}[^\n]*\n[\s\S]*?\={7}[^\n]*\n[\s\S]*?>{7}[^\n]*\n")
    resolved_footer = """    <div class="modal-footer border-top-0 pt-0 d-flex flex-wrap gap-2 justify-content-end">
        <button type="button" class="btn btn-light rounded-pill px-4 flex-fill flex-sm-grow-0" data-bs-dismiss="modal">Cancel</button>
        <button type="submit" class="btn btn-primary text-white fw-bold rounded-pill px-4 flex-fill flex-sm-grow-0">Save Policy</button>
    </div>
"""
    content = pattern.sub(resolved_footer, content, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved policy_form.html")

def resolve_budgets():
    path = "templates/pages/dashboards/superadmin/budgets.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Conflict 1
    pattern = re.compile(r"<{7}[^\n]*\n[\s\S]*?\={7}[^\n]*\n[\s\S]*?>{7}[^\n]*\n")
    resolved_btn = """            <button hx-get="/superadmin/budgets/create/" hx-target="#modal-content-body" data-bs-toggle="modal" data-bs-target="#modal-container" class="btn btn-primary text-white fw-bold rounded-pill px-3 px-sm-4 shadow-sm flex-fill flex-sm-grow-0 text-nowrap">
                <i class="fa-solid fa-plus me-1"></i> Add Budget
            </button>
"""
    content = pattern.sub(resolved_btn, content, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved budgets.html")

def resolve_superadmin_base():
    path = "templates/layouts/superadmin_base.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"(<{7}[^\n]*\n)([\s\S]*?)(\={7}[^\n]*\n)([\s\S]*?)(>{7}[^\n]*\n)")
    matches = list(pattern.finditer(content))
    assert len(matches) == 4, f"Expected 4 conflicts in superadmin_base.html, found {len(matches)}"

    # Match 1: legacy sidebar backdrop & layout (upstream) vs empty (stashed) -> take stashed (empty)
    # Match 2: upstream styling vs stashed .sa-navlink:hover -> take stashed
    # Match 3: upstream styling vs stashed comment -> take stashed
    # Match 4: upstream responsive styles (sa-tabs-scroll badge, mobile media queries, modal rules) vs empty -> keep upstream responsive rules!

    # We do replacement from back to front so indices don't shift
    # Match 4
    m4_upstream = matches[3].group(2)
    content = content[:matches[3].start()] + m4_upstream + content[matches[3].end():]

    # Re-find matches
    matches = list(pattern.finditer(content))
    # Match 3
    m3_stashed = matches[2].group(4)
    content = content[:matches[2].start()] + m3_stashed + content[matches[2].end():]

    matches = list(pattern.finditer(content))
    # Match 2
    m2_stashed = matches[1].group(4)
    content = content[:matches[1].start()] + m2_stashed + content[matches[1].end():]

    matches = list(pattern.finditer(content))
    # Match 1
    m1_stashed = matches[0].group(4)  # empty
    content = content[:matches[0].start()] + m1_stashed + content[matches[0].end():]

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved superadmin_base.html")

def resolve_base_manager():
    path = "templates/manager/base_manager.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"(<{7}[^\n]*\n)([\s\S]*?)(\={7}[^\n]*\n)([\s\S]*?)(>{7}[^\n]*\n)")
    matches = list(pattern.finditer(content))
    assert len(matches) == 1, f"Expected 1 conflict in base_manager.html, found {len(matches)}"

    # In base_manager.html: Upstream has the old drawer + old nav with bottom footer & duplicate logout.
    # Stashed has the new drawer header matching Vendor theme.
    # We replace conflict 1 with stashed group 4:
    stashed_header = matches[0].group(4)
    content = content[:matches[0].start()] + stashed_header + content[matches[0].end():]

    # Also ensure Vendor Suspension is present under Suppliers
    if "/manager/vendor-risk/suspension/" not in content:
        suspension_nav = """            <a href="/manager/vendor-risk/suspension/" class="manager-nav-link {% if '/manager/vendor-risk/suspension/' in request.path %}active{% endif %}">
                <i class="fa-solid fa-scale-balanced nav-icon text-cyan"></i>
                <span>Vendor Suspension</span>
            </a>\n"""
        target = '<span>Vendor Risk</span>\n            </a>'
        assert target in content, "Vendor Risk nav item not found"
        content = content.replace(target, target + "\n" + suspension_nav, 1)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved base_manager.html")

def resolve_manager_dashboard():
    path = "templates/manager/dashboard.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(r"(<{7}[^\n]*\n)([\s\S]*?)(\={7}[^\n]*\n)([\s\S]*?)(>{7}[^\n]*\n)")
    matches = list(pattern.finditer(content))
    assert len(matches) == 9, f"Expected 9 conflicts in manager/dashboard.html, found {len(matches)}"

    # For all 9 conflicts in manager/dashboard.html, stashed version is the standardized Vendor dashboard design:
    # 1. Dark charcoal banner
    # 2. Card 1 with 2px #FFC107 border
    # 3. Card 2 with 2px #DC3545 border
    # 4. Card 3 with 2px #0D6EFD border
    # 5. Card 4 with 2px #DC3545 border
    # 6. Budget Card with 1px border
    # 7. Quality Card with 1px border
    # 8. Watchlist Card with 1px border
    # 9. Modules Card with 1px border
    # We replace from back to front with stashed changes (group 4)
    for m in reversed(matches):
        stashed_text = m.group(4)
        content = content[:m.start()] + stashed_text + content[m.end():]

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved manager/dashboard.html")

if __name__ == "__main__":
    resolve_policy_form()
    resolve_budgets()
    resolve_superadmin_base()
    resolve_base_manager()
    resolve_manager_dashboard()
    print("All 5 conflicted files resolved successfully!")

