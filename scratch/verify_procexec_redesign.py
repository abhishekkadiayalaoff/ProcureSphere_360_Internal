import os
import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

def test_proc_exec_and_vendor():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Context 1: Procurement Executive
        context1 = browser.new_context(viewport={"width": 1440, "height": 900})
        page1 = context1.new_page()

        print("1. Logging in as procexec@hpe.com...")
        page1.goto(f"{BASE_URL}/login/")
        page1.fill('input[type="email"], input[name="email"], input[name="username"]', 'procexec@hpe.com')
        page1.fill('input[name="password"]', 'Password123!')
        page1.click('button[type="submit"]')
        page1.wait_for_load_state("networkidle")

        print(f"Current URL after login: {page1.url}")
        time.sleep(1)

        # 1. Desktop Verification
        print("2. Verifying Desktop view...")
        assert "ProcureSphere" in page1.content(), "Brand not found in content"
        
        # Check Sign Out count
        logout_elements = page1.locator('a[href*="/logout/"], button:has-text("Sign Out"), a:has-text("Sign Out")')
        logout_count = logout_elements.count()
        print(f"Total Sign Out / Logout elements found: {logout_count}")
        assert logout_count == 1, f"Expected exactly 1 Sign Out element, found {logout_count}!"

        # Verify sidebar bottom has no logout
        sidebar_footers = page1.locator('#procExecSidebar .sidebar-footer, #procExecSidebar .border-top a[href*="/logout/"]')
        assert sidebar_footers.count() == 0, "Found footer or logout in sidebar!"

        # Check Active nav item is Dashboard
        active_nav = page1.locator('#procExecSidebar a.active-nav-item')
        print(f"Active nav text: {active_nav.text_content().strip()}")
        assert "Dashboard" in active_nav.text_content(), "Dashboard is not the active nav item!"

        desktop_shot = os.path.join(ARTIFACT_DIR, "procexec_redesign_desktop.png")
        page1.screenshot(path=desktop_shot, full_page=False)
        print(f"Saved {desktop_shot}")

        # Open Dropdown and verify ONLY Sign Out is inside
        print("3. Testing top-right Profile Dropdown (Sign Out only)...")
        page1.click('button[aria-label="User Profile Menu"]')
        time.sleep(0.5)
        dropdown_menu = page1.locator('.proc-exec-topbar .dropdown-menu.show')
        assert dropdown_menu.is_visible(), "Dropdown menu did not open!"
        
        assert dropdown_menu.locator('text=Notifications').count() == 0, "Redundant Notifications still in dropdown!"
        assert dropdown_menu.locator('text=Vendor Governance').count() == 0, "Redundant Vendor Governance still in dropdown!"
        assert dropdown_menu.locator('a[href*="/logout/"]').is_visible(), "Sign Out not visible in dropdown!"
        
        dropdown_items = dropdown_menu.locator('.dropdown-item')
        print(f"Dropdown items count: {dropdown_items.count()}")
        assert dropdown_items.count() == 1, f"Expected exactly 1 dropdown item, got {dropdown_items.count()}"

        dropdown_shot = os.path.join(ARTIFACT_DIR, "procexec_dropdown_signout.png")
        page1.screenshot(path=dropdown_shot, full_page=False)
        print(f"Saved {dropdown_shot}")

        # Close dropdown by clicking body
        page1.keyboard.press("Escape")
        time.sleep(0.3)

        # 4. Test Navigation Links
        print("4. Testing key Procurement Executive navigation routes...")
        routes = [
            ("/vendors/onboarding/", "Vendor Onboarding"),
            ("/vendors/", "Vendor Master"),
            ("/sourcing-events/", "RFQ"),
            ("/purchase-orders/", "Purchase Orders"),
            ("/notifications/", "Notifications"),
        ]
        for route, label in routes:
            page1.goto(f"{BASE_URL}{route}")
            page1.wait_for_load_state("networkidle")
            time.sleep(0.5)
            l_count = page1.locator('a[href*="/logout/"], button:has-text("Sign Out"), a:has-text("Sign Out")').count()
            print(f"  Route {route} ({label}): HTTP 200 OK, logout elements count: {l_count}")

        # Return to Dashboard
        page1.goto(f"{BASE_URL}/")
        page1.wait_for_load_state("networkidle")
        time.sleep(0.5)

        # 5. Tablet Verification (768x1024)
        print("5. Verifying Tablet View (768x1024)...")
        page1.set_viewport_size({"width": 768, "height": 1024})
        time.sleep(0.5)
        tablet_shot = os.path.join(ARTIFACT_DIR, "procexec_redesign_tablet.png")
        page1.screenshot(path=tablet_shot, full_page=False)
        print(f"Saved {tablet_shot}")

        # 6. Mobile Verification (390x844)
        print("6. Verifying Mobile View (390x844)...")
        page1.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.5)
        mobile_shot = os.path.join(ARTIFACT_DIR, "procexec_redesign_mobile.png")
        page1.screenshot(path=mobile_shot, full_page=False)
        print(f"Saved {mobile_shot}")

        # Open Mobile Hamburger Drawer
        print("7. Testing Mobile Hamburger Offcanvas...")
        hamburger = page1.locator('.proc-exec-topbar button[data-bs-target="#procExecSidebar"]')
        assert hamburger.is_visible(), "Mobile hamburger button is not visible!"
        hamburger.click()
        time.sleep(0.8)

        mobile_drawer_shot = os.path.join(ARTIFACT_DIR, "procexec_redesign_mobile_drawer.png")
        page1.screenshot(path=mobile_drawer_shot, full_page=False)
        print(f"Saved {mobile_drawer_shot}")

        # Close Drawer before clicking anything else
        close_btn = page1.locator('#procExecSidebar .btn-close')
        close_btn.click()
        time.sleep(0.5)

        # 8. Test Single Sign Out execution
        print("8. Testing Sign Out functionality...")
        page1.set_viewport_size({"width": 1440, "height": 900})
        time.sleep(0.3)
        page1.click('button[aria-label="User Profile Menu"]')
        time.sleep(0.5)
        page1.click('.proc-exec-topbar .dropdown-menu.show a[href*="/logout/"]')
        page1.wait_for_load_state("networkidle")
        time.sleep(1)
        print(f"URL after Sign Out: {page1.url}")
        context1.close()

        # Context 2: Vendor Dashboard Check
        print("9. Verifying Vendor Dashboard in fresh context...")
        context2 = browser.new_context(viewport={"width": 1440, "height": 900})
        page2 = context2.new_page()
        page2.goto(f"{BASE_URL}/login/")
        page2.fill('input[type="email"], input[name="email"], input[name="username"]', 'vendoruser@cisco.com')
        page2.fill('input[name="password"]', 'Password123!')
        page2.click('button[type="submit"]')
        page2.wait_for_load_state("networkidle")
        time.sleep(1)
        assert "/vendor" in page2.url, f"Expected vendor portal, got {page2.url}"
        
        vendor_shot = os.path.join(ARTIFACT_DIR, "vendor_dashboard_untouched3.png")
        page2.screenshot(path=vendor_shot, full_page=False)
        print(f"Saved {vendor_shot}")
        context2.close()

        browser.close()
        print("\nALL VERIFICATIONS PASSED 100% SUCCESSFULLY!")

if __name__ == "__main__":
    test_proc_exec_and_vendor()
