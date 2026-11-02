import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

ROLES_TO_TEST = [
    ("superadmin", "admin@hpe.com", "Password123!", "/superadmin/dashboard/"),
    ("requester", "requester@hpe.com", "Password123!", "/dashboard/"),
    ("approver", "approver@hpe.com", "Password123!", "/approver/dashboard/"),
    ("procexec", "procexec@hpe.com", "Password123!", "/dashboard/"),
    ("procmgr", "procmgr@hpe.com", "Password123!", "/manager/dashboard/"),
    ("stores", "receiver@hpe.com", "Password123!", "/receipts/dashboard/"),
    ("legal", "legal@hpe.com", "Password123!", "/contracts/dashboard/"),
    ("auditor", "auditor@hpe.com", "Password123!", "/audit/dashboard/"),
    ("vendor", "vendoruser@cisco.com", "Password123!", "/vendor/dashboard/"),
]

async def test_role(browser, name, email, password, target_url):
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    
    print(f"\n--- Testing {name} ({email}) ---")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('#email', email)
    await page.fill('#password', password)
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    
    if target_url not in page.url and page.url != f"{BASE_URL}/":
        await page.goto(f"{BASE_URL}{target_url}")
        await page.wait_for_load_state("networkidle")

    # Find sign out link
    signout_links = await page.query_selector_all('a[href*="/logout"]')
    print(f"[{name}] Total /logout links found: {len(signout_links)}")
    assert len(signout_links) >= 1, f"[{name}] No Sign Out link found!"

    # Header signout button
    header_signout = signout_links[0]
    is_visible = await header_signout.is_visible()
    text = (await header_signout.inner_text()).strip()
    print(f"[{name}] Header Sign Out visible: {is_visible}, text: '{text}'")
    assert is_visible, f"[{name}] Sign Out button is not visible in header!"

    # Header screenshot
    header = await page.query_selector("nav.navbar, header, nav")
    if header:
        shot_path = os.path.join(ARTIFACT_DIR, f"{name}_header_signout_verified.png")
        await header.screenshot(path=shot_path)
        print(f"[{name}] Saved header screenshot: {shot_path}")

    await context.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for role_info in ROLES_TO_TEST:
            await test_role(browser, *role_info)
        await browser.close()
        print("\nALL 9 DASHBOARDS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())

