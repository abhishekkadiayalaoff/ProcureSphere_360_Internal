base_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\base.html"

with open(base_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """                        <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white py-1">
                            <li><a class="dropdown-item text-white py-2" href="{% url 'notification_list' %}"><i class="fa-solid fa-bell text-warning me-2"></i> Notifications</a></li>
                            <li><a class="dropdown-item text-white py-2" href="{% url 'vendor_governance' %}"><i class="fa-solid fa-shield-halved text-cyan me-2"></i> Vendor Governance</a></li>
                            <li><hr class="dropdown-divider border-secondary"></li>
                            <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                        </ul>"""

replacement = """                        <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white py-1">
                            <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                        </ul>"""

if target in content:
    content = content.replace(target, replacement)
    with open(base_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully replaced dropdown content with Sign Out only.")
else:
    print("Target not found.")

