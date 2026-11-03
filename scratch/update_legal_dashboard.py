import os

# 1. Update templates/layouts/legal_base.html
legal_base_path = r'ProcureSphere_360_Internal/templates/layouts/legal_base.html'
with open(legal_base_path, 'r', encoding='utf-8') as f:
    base_content = f.read().replace('\r\n', '\n')

# Remove bottom footnote
old_footnote = """                <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 px-1">
                    <div class="d-flex align-items-center text-muted small" style="font-size: 0.68rem;">
                        <i class="fa-solid fa-lock text-success me-2"></i>
                        <span>SLA Enforcement &bull; Legal Compliance</span>
                    </div>
                </div>"""

if old_footnote in base_content:
    base_content = base_content.replace(old_footnote, "", 1)
    print("SLA Enforcement footnote removed successfully.")
else:
    print("SLA Enforcement footnote not found!")

# Update header user profile & sign out to match design system with direct Sign Out pill button
old_header_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                    <div class="text-muted d-block" style="font-size: 0.7rem; line-height: 1;">Legal Counsel / Manager</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fa-solid fa-user-tie text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white">
                        <li><a class="dropdown-item text-white py-2" href="/contracts/create/"><i class="fa-solid fa-file-signature text-cyan me-2"></i> New Contract Draft</a></li>
                        <li><a class="dropdown-item text-white py-2" href="/contracts/"><i class="fa-solid fa-file-contract text-info me-2"></i> Contract Register</a></li>
                        <li><hr class="dropdown-divider border-secondary"></li>
                        <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}"""

new_header_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Legal Counsel / Manager</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""

if old_header_user in base_content:
    base_content = base_content.replace(old_header_user, new_header_user, 1)
    print("Header user profile updated successfully.")
else:
    print("Header user profile not found!")

with open(legal_base_path, 'w', encoding='utf-8') as f:
    f.write(base_content)

# 2. Update templates/pages/dashboards/legal_dashboard.html
legal_dash_path = r'ProcureSphere_360_Internal/templates/pages/dashboards/legal_dashboard.html'
with open(legal_dash_path, 'r', encoding='utf-8') as f:
    dash_content = f.read().replace('\r\n', '\n')

# Update hover style
old_hover = """    .kpi-card-link:hover .kpi-card {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -4px rgba(15, 23, 42, 0.12) !important;
        border-color: rgba(13, 110, 253, 0.4) !important;
    }"""

new_hover = """    .kpi-card-link:hover .kpi-card {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px -4px rgba(15, 23, 42, 0.12) !important;
    }"""

if old_hover in dash_content:
    dash_content = dash_content.replace(old_hover, new_hover, 1)
    print("Hover style updated successfully.")
else:
    print("Hover style not found!")

card_replacements = [
    # Card 1: Pending Legal Review (Yellow / Amber)
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-warning">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #FFC107 !important; border-radius: 14px;">'
    ),
    # Card 2: Active Contracts (Primary Blue)
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-primary">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #0D6EFD !important; border-radius: 14px;">'
    ),
    # Card 3: Expiring Contracts (<30 Days) (Danger Red)
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-danger">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #DC3545 !important; border-radius: 14px;">'
    ),
    # Card 4: Total Contract Value (Success Green)
    (
        '<div class="card kpi-card border-0 shadow-sm rounded-4 h-100 bg-white border-start border-4 border-success">',
        '<div class="card kpi-card shadow-sm rounded-4 h-100 bg-white" style="border: 2px solid #198754 !important; border-radius: 14px;">'
    ),
]

for idx, (old, new) in enumerate(card_replacements, 1):
    if old in dash_content:
        dash_content = dash_content.replace(old, new, 1)
        print(f"Legal Dashboard Card {idx} updated successfully.")
    else:
        print(f"Legal Dashboard Card {idx} NOT found!")

with open(legal_dash_path, 'w', encoding='utf-8') as f:
    f.write(dash_content)

print("Legal updates complete.")

