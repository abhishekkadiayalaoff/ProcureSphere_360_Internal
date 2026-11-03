import os

updates = [
    # 1. Super Admin
    (
        r'ProcureSphere_360_Internal/templates/layouts/superadmin_base.html',
        """            <!-- User Profile & Sign Out Dropdown (Exact Vendor Dashboard Pattern) -->
            {% if request.user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ request.user.email|default:"admin@hpe.com" }}</div>
                    <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Super Administrator</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false" title="Account Menu">
                        <i class="fa-solid fa-user-shield text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white py-1">
                        <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}""",
        """            <!-- User Profile & Sign Out -->
            {% if request.user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ request.user.email|default:"admin@hpe.com" }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Super Administrator</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""
    ),

    # 2. Requester
    (
        r'ProcureSphere_360_Internal/templates/layouts/requester_base.html',
        """            <!-- User Profile & Sign Out (Dropdown matching Vendor Dashboard) -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-0">{{ user.email }}</div>
                    <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Purchase Requester</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="User Profile Menu">
                        <i class="fa-solid fa-user text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border border-secondary border-opacity-25 bg-dark text-white py-1">
                        <li><a class="dropdown-item text-danger py-2 d-flex align-items-center" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}""",
        """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Purchase Requester</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""
    ),

    # 3. Department Approver
    (
        r'ProcureSphere_360_Internal/templates/layouts/approver_base.html',
        """            <!-- User Profile & Sign Out Dropdown (ONLY ONE Sign Out on entire dashboard) -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-0">{{ user.email|default:"approver@hpe.com" }}</div>
                    <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Department Approver</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="User Profile Menu">
                        <i class="fa-solid fa-user-check text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border border-secondary border-opacity-25 bg-dark text-white py-1">
                        <li><a class="dropdown-item text-danger py-2 d-flex align-items-center" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}""",
        """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email|default:"approver@hpe.com" }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Department Approver</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""
    ),

    # 4. Procurement Executive (base.html)
    (
        r'ProcureSphere_360_Internal/templates/base.html',
        """                <!-- User Profile & Dropdown (Single Sign Out Point) -->
                <div class="d-flex align-items-center gap-2">
                    <div class="d-none d-lg-block text-end lh-sm me-1">
                        <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                        <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Procurement Executive</div>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="User Profile Menu">
                            <i class="fa-solid fa-user-tie text-cyan"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white py-1">
                            <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                        </ul>
                    </div>
                </div>""",
        """                <!-- User Profile & Sign Out -->
                <div class="d-flex align-items-center gap-2">
                    <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                        <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                        <div class="text-start leading-tight me-1">
                            <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                            <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Procurement Executive</div>
                        </div>
                    </div>
                    <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                    </a>
                </div>"""
    ),

    # 5. Procurement Manager
    (
        r'ProcureSphere_360_Internal/templates/manager/base_manager.html',
        """            <!-- User Profile & Dropdown (ONLY ONE Sign Out on entire dashboard) -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-lg-block text-end lh-sm me-1">
                    <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                    <div class="text-white-50 d-block" style="font-size: 0.7rem; line-height: 1;">Procurement Manager</div>
                </div>
                <div class="dropdown">
                    <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false" aria-label="User Profile Menu">
                        <i class="fa-solid fa-user-tie text-cyan"></i>
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-lg border border-secondary border-opacity-25 bg-dark text-white py-1">
                        <li><a class="dropdown-item text-danger py-2 d-flex align-items-center" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                    </ul>
                </div>
            </div>
            {% endif %}""",
        """            <!-- User Profile & Sign Out -->
            {% if user.is_authenticated %}
            <div class="d-flex align-items-center gap-2">
                <div class="d-none d-md-flex align-items-center px-2 px-sm-3 py-1 bg-secondary bg-opacity-25 rounded-pill border border-secondary border-opacity-50 text-white">
                    <i class="fa-solid fa-circle-user text-cyan me-1 me-sm-2 fs-5"></i>
                    <div class="text-start leading-tight me-1">
                        <div class="fw-semibold text-white small text-truncate" style="max-width: 140px;">{{ user.email }}</div>
                        <div class="badge bg-secondary bg-opacity-75 text-cyan rounded-pill" style="font-size: 0.65rem;">Procurement Manager</div>
                    </div>
                </div>
                <a href="/logout/" class="btn btn-outline-light btn-sm rounded-pill px-2.5 px-sm-3 text-nowrap d-inline-flex align-items-center" title="Sign Out">
                    <i class="fa-solid fa-arrow-right-from-bracket"></i> <span class="d-none d-sm-inline ms-1">Sign Out</span>
                </a>
            </div>
            {% endif %}"""
    ),
]

for file_path, old_block, new_block in updates:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().replace('\r\n', '\n')
    
    if old_block in content:
        content = content.replace(old_block, new_block, 1)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path} successfully.")
    else:
        print(f"FAILED to find block in {file_path}!")

print("All updates attempted.")

