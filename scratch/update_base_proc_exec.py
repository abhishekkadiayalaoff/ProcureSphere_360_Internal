import os

base_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\base.html"
with open(base_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update notification icon & profile dropdown
old_topbar_right = """                <!-- Notifications Icon -->
                <a href="{% url 'notification_list' %}" class="btn btn-outline-secondary btn-sm position-relative text-white border-0 d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" title="Notifications">
                    <i class="fa-solid fa-bell fs-5"></i>
                </a>

                <!-- User Profile & Dropdown -->
                <div class="d-flex align-items-center gap-2">
                    <div class="d-none d-lg-block text-end lh-sm me-1">
                        <div class="fw-semibold text-white small mb-1">{{ user.email }}</div>
                        <div class="text-muted d-block" style="font-size: 0.7rem; line-height: 1;">Procurement Executive</div>
                    </div>
                    <div class="dropdown">
                        <button class="btn btn-dark border border-secondary border-opacity-50 rounded-circle text-white d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                            <i class="fa-solid fa-user-tie text-cyan"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end shadow-lg border-0 bg-dark text-white">
                            <li><a class="dropdown-item text-white py-2" href="{% url 'notification_list' %}"><i class="fa-solid fa-bell text-warning me-2"></i> Notifications</a></li>
                            <li><a class="dropdown-item text-white py-2" href="{% url 'vendor_governance' %}"><i class="fa-solid fa-shield-halved text-cyan me-2"></i> Vendor Governance</a></li>
                            <li><hr class="dropdown-divider border-secondary"></li>
                            <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                        </ul>
                    </div>
                </div>"""

new_topbar_right = """                <!-- Notifications Icon -->
                <a href="{% url 'notification_list' %}" class="btn btn-outline-secondary btn-sm position-relative text-white border-0 d-flex align-items-center justify-content-center p-0" style="width: 36px; height: 36px;" title="Notifications">
                    <i class="fa-solid fa-bell fs-5"></i>
                    {% if unread_notifications_count and unread_notifications_count > 0 %}
                    <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="font-size: 0.65rem;">
                        {{ unread_notifications_count }}
                        <span class="visually-hidden">unread notifications</span>
                    </span>
                    {% endif %}
                </a>

                <!-- User Profile & Dropdown (Single Sign Out Point) -->
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
                            <li><a class="dropdown-item text-white py-2" href="{% url 'notification_list' %}"><i class="fa-solid fa-bell text-warning me-2"></i> Notifications</a></li>
                            <li><a class="dropdown-item text-white py-2" href="{% url 'vendor_governance' %}"><i class="fa-solid fa-shield-halved text-cyan me-2"></i> Vendor Governance</a></li>
                            <li><hr class="dropdown-divider border-secondary"></li>
                            <li><a class="dropdown-item text-danger py-2" href="/logout/"><i class="fa-solid fa-arrow-right-from-bracket me-2"></i> Sign Out</a></li>
                        </ul>
                    </div>
                </div>"""

# 2. Update main background
old_main = """        <main class="{% if user.is_authenticated and user.role_code == 'PROC_EXEC' %}flex-grow-1 p-2 p-sm-3 p-md-4 bg-light w-100{% else %}container-fluid p-3 p-md-4 overflow-auto{% endif %}" style="min-width: 0; {% if user.is_authenticated and user.role_code == 'PROC_EXEC' %}max-width: 100vw; overflow-x: hidden;{% endif %}">"""

new_main = """        <main class="{% if user.is_authenticated and user.role_code == 'PROC_EXEC' %}flex-grow-1 p-2 p-sm-3 p-md-4 w-100{% else %}container-fluid p-3 p-md-4 overflow-auto{% endif %}" style="min-width: 0; background-color: #F5F7FA; {% if user.is_authenticated and user.role_code == 'PROC_EXEC' %}max-width: 100vw; overflow-x: hidden;{% endif %}">"""

if old_topbar_right in content:
    content = content.replace(old_topbar_right, new_topbar_right)
    print("Topbar updated successfully.")
else:
    print("WARNING: old_topbar_right not found.")

if old_main in content:
    content = content.replace(old_main, new_main)
    print("Main background updated successfully.")
else:
    print("WARNING: old_main not found.")

with open(base_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done base.html update.")

