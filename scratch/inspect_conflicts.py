import re

def inspect_file(filepath):
    print("=" * 60)
    print("INSPECTING:", filepath)
    print("=" * 60)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    pattern = re.compile(r"(<{7}[^\n]*\n)([\s\S]*?)(\={7}[^\n]*\n)([\s\S]*?)(>{7}[^\n]*\n)")
    matches = list(pattern.finditer(content))
    print(f"Total conflict blocks: {len(matches)}")
    for idx, m in enumerate(matches, 1):
        print(f"\n--- Conflict #{idx} ---")
        print("UPSTREAM:")
        print(m.group(2)[:300] + ("..." if len(m.group(2)) > 300 else ""))
        print("STASHED:")
        print(m.group(4)[:300] + ("..." if len(m.group(4)) > 300 else ""))

for p in [
    "templates/pages/dashboards/superadmin/policy_form.html",
    "templates/pages/dashboards/superadmin/budgets.html",
    "templates/layouts/superadmin_base.html",
    "templates/manager/base_manager.html",
    "templates/manager/dashboard.html"
]:
    inspect_file(p)

