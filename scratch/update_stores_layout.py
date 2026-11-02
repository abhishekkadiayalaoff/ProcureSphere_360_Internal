path = r'ProcureSphere_360_Internal/templates/layouts/stores_base.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('\r\n', '\n')

# 1. Update dropdown menu to Sign Out only
old_dropdown = """                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white">
                        <li><a class="dropdown-item text-white py-2" href="{% url 'orders_list' %}"><i class="fa-solid fa-cart-flatbed text-cyan me-2"></i> Receive PO Goods</a></li>
                        <li><a class="dropdown-item text-white py-2" href="{% url 'receipts_list' %}"><i class="fa-solid fa-boxes-stacked text-info me-2"></i> Goods Receipts (GRN)</a></li>
                        <li><hr class="dropdown-divider border-secondary"></li>
                        <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>"""

new_dropdown = """                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white p-1" style="min-width: 160px;">
                        <li>
                            <a class="dropdown-item text-danger py-2 rounded-2 d-flex align-items-center" href="/logout/">
                                <i class="fa-solid fa-arrow-right-from-bracket me-2 text-danger"></i>
                                <span class="fw-medium">Sign Out</span>
                            </a>
                        </li>
                    </ul>"""

if old_dropdown in content:
    content = content.replace(old_dropdown, new_dropdown, 1)
    print("Dropdown updated successfully to Sign Out only.")
else:
    print("Old dropdown NOT found!")

# 2. Remove bottom footnote "Physical Intake • Quality Verified"
old_footnote = """                <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 px-1">
                    <div class="d-flex align-items-center text-muted small" style="font-size: 0.68rem;">
                        <i class="fa-solid fa-lock text-success me-2"></i>
                        <span>Physical Intake &bull; Quality Verified</span>
                    </div>
                </div>"""

if old_footnote in content:
    content = content.replace(old_footnote, "", 1)
    print("Footnote removed successfully.")
else:
    print("Footnote NOT found!")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Stores layout update complete.")

