# 1. Update dashboard.html for Card 4 border
dashboard_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\dashboard.html"
with open(dashboard_path, "r", encoding="utf-8") as f:
    dash_text = f.read()

old_card4 = """        <!-- 4. High-Risk & Suspended Vendors (Neutral Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/vendor-risk/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #DEE2E6 !important; border-radius: 14px;">"""

new_card4 = """        <!-- 4. High-Risk & Suspended Vendors (Red Border) -->
        <div class="col-sm-6 col-xl-3">
            <a href="/manager/vendor-risk/" class="text-decoration-none">
                <div class="card h-100 shadow-sm rounded-4 p-3 hover-elevate transition-all" style="background-color: #FFFFFF; border: 2px solid #DC3545 !important; border-radius: 14px;">"""

if old_card4 in dash_text:
    dash_text = dash_text.replace(old_card4, new_card4)
    with open(dashboard_path, "w", encoding="utf-8") as f:
        f.write(dash_text)
    print("Updated Card 4 border to 2px solid #DC3545 in dashboard.html successfully!")
else:
    print("Warning: old_card4 not found in dashboard.html!")


# 2. Update base_manager.html to remove the sidebar footnote
base_path = r"c:\Users\windows10\Desktop\PRO 360\ProcureSphere_360_Internal\templates\manager\base_manager.html"
with open(base_path, "r", encoding="utf-8") as f:
    base_text = f.read()

footnote_block = """            <!-- Security Footnote (NO DUPLICATE LOGOUT, NO DUPLICATE FOOTER) -->
            <div class="mt-4 pt-3 border-top border-secondary border-opacity-25 px-2 mb-2">
                <div class="d-flex align-items-center text-white-50 small" style="font-size: 0.68rem;">
                    <i class="fa-solid fa-lock text-success me-2"></i>
                    <span>RBAC Backend Enforced &bull; Manager Governance</span>
                </div>
            </div>"""

if footnote_block in base_text:
    base_text = base_text.replace(footnote_block, "")
    with open(base_path, "w", encoding="utf-8") as f:
        f.write(base_text)
    print("Removed sidebar footnote from base_manager.html successfully!")
else:
    print("Warning: footnote_block not found in base_manager.html!")

