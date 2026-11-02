import os

auditor_base_path = r'ProcureSphere_360_Internal/templates/audit/base_auditor.html'
with open(auditor_base_path, 'r', encoding='utf-8') as f:
    content = f.read().replace('\r\n', '\n')

# 1. Update header user profile & Sign Out
old_header = """            <!-- User Profile & Dropdown -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ user.email|default:"auditor@hpe.com" }}</div>
                    <div class="text-muted d-block" style="font-size: 0.7rem; line-height: 1;">Compliance Auditor</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fa-solid fa-user-shield text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white small">
                        <li><a class="dropdown-item text-white py-2" href="/audit/logs/"><i class="fa-solid fa-fingerprint text-cyan me-2"></i> Audit Logs</a></li>
                        <li><a class="dropdown-item text-white py-2" href="/audit/lifecycle/"><i class="fa-solid fa-diagram-project text-cyan me-2"></i> Lifecycle Explorer</a></li>
                        <li><hr class="dropdown-divider border-secondary"></li>
                        <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}"""

new_header = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email|default:"auditor@hpe.com" }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Compliance Auditor</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""

if old_header in content:
    content = content.replace(old_header, new_header, 1)
    print("Header user profile updated successfully.")
else:
    print("Header user profile NOT found!")

# 2. Remove Security Footnote
old_footnote = """                <!-- Security Footnote -->
                <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 px-2 mb-2">
                    <div class="d-flex align-items-center text-muted small" style="font-size: 0.68rem;">
                        <i class="fa-solid fa-lock text-success me-2"></i>
                        <span>Immutable Audit Trail &bull; WORM Compliant</span>
                    </div>
                </div>"""

if old_footnote in content:
    content = content.replace(old_footnote, "", 1)
    print("Immutable Audit Trail footnote removed successfully.")
else:
    print("Immutable Audit Trail footnote NOT found!")

# 3. Remove Sidebar Footer (user profile + sign out + version badge)
old_footer = """        <!-- Sidebar Footer -->
        <div class="sidebar-footer border-top border-secondary border-opacity-25 px-3 py-3 mt-auto">
            <div class="d-flex align-items-center justify-content-between gap-2 mb-2 w-100">
                <div class="d-flex align-items-center overflow-hidden me-2" style="min-width: 0; flex: 1 1 auto;">
                    <i class="fa-solid fa-circle-user text-info fs-4 me-2 flex-shrink-0"></i>
                    <div class="overflow-hidden" style="min-width: 0; flex: 1 1 auto;">
                        <div class="small fw-semibold text-white text-truncate" title="{{ user.email }}">{{ user.email|default:"auditor@hpe.com" }}</div>
                        <div class="badge bg-info text-dark rounded-pill" style="font-size: 0.65rem;">Compliance Auditor</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-circle flex-shrink-0 d-inline-flex align-items-center justify-content-center" style="width: 32px; height: 32px; padding: 0;" title="Sign out"><i class="fa-solid fa-arrow-right-from-bracket"></i><span class="visually-hidden">Sign out</span></a>
            </div>
            <div class="d-flex align-items-center justify-content-between small text-white-50 pt-2 border-top border-secondary border-opacity-25">
                <span class="d-flex align-items-center text-truncate me-2">
                    <i class="fa-solid fa-shield-halved me-2 text-info"></i>
                    <span class="text-truncate">Read-Only Evidence Vault</span>
                </span>
                <span class="badge bg-secondary bg-opacity-25 text-white-50 border border-secondary border-opacity-50">v2026.1</span>
            </div>
        </div>"""

if old_footer in content:
    content = content.replace(old_footer, "", 1)
    print("Sidebar footer removed successfully.")
else:
    print("Sidebar footer NOT found!")

with open(auditor_base_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("base_auditor.html update complete.")

