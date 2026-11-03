import os

# 1. Update stores_base.html
stores_path = r'ProcureSphere_360_Internal/templates/layouts/stores_base.html'
with open(stores_path, 'r', encoding='utf-8') as f:
    stores_content = f.read().replace('\r\n', '\n')

old_stores_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                    <div class="text-muted d-block" style="font-size: 0.7rem; line-height: 1;">Warehouse Specialist</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fa-solid fa-user-tie text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white p-1" style="min-width: 160px;">
                        <li>
                            <a class="dropdown-item text-danger py-2 rounded-2 d-flex align-items-center" href="/logout/">
                                <i class="fa-solid fa-arrow-right-from-bracket me-2 text-danger"></i>
                                <span class="fw-medium">Sign Out</span>
                            </a>
                        </li>
                    </ul>
                </div>
            </div>
            {% endif %}"""

new_stores_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Warehouse Specialist</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""

if old_stores_user in stores_content:
    stores_content = stores_content.replace(old_stores_user, new_stores_user, 1)
    with open(stores_path, 'w', encoding='utf-8') as f:
        f.write(stores_content)
    print("stores_base.html updated successfully with visible Sign Out button.")
else:
    print("old_stores_user not found in stores_base.html!")

# 2. Update vendor_base.html
vendor_path = r'ProcureSphere_360_Internal/templates/layouts/vendor_base.html'
with open(vendor_path, 'r', encoding='utf-8') as f:
    vendor_content = f.read().replace('\r\n', '\n')

old_vendor_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                    <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Authorized Representative</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fa-solid fa-user-tie text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white py-1">
                        <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}"""

new_vendor_user = """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Authorized Representative</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""

if old_vendor_user in vendor_content:
    vendor_content = vendor_content.replace(old_vendor_user, new_vendor_user, 1)
    with open(vendor_path, 'w', encoding='utf-8') as f:
        f.write(vendor_content)
    print("vendor_base.html updated successfully with visible Sign Out button.")
else:
    print("old_vendor_user not found in vendor_base.html!")

