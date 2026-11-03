import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("--- Testing Vendor Dashboard ---")
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'vendoruser@cisco.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        await page.goto(f"{BASE_URL}/vendor/dashboard/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1000)

        # Check body text
        body_text = await page.inner_text('body')
        assert "RBAC Backend Enforced • Sealed Bids" not in body_text, "Footnote still present!"
        assert "Sealed Bids" not in body_text or "Sourcing" in body_text, "Check sealed bids"
        print("Footnote 'RBAC Backend Enforced • Sealed Bids' successfully removed!")

        # Screenshot sidebar
        sidebar = await page.query_selector('#vendorSidebar')
        if sidebar:
            await sidebar.screenshot(path=os.path.join(ARTIFACT_DIR, "vendor_sidebar_no_footnote.png"))
            print("Saved sidebar screenshot: vendor_sidebar_no_footnote.png")

        # Full page screenshot
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "vendor_dashboard_verified_no_footnote.png"))
        print("Saved full page screenshot: vendor_dashboard_verified_no_footnote.png")

        await browser.close()
        print("ALL CHECKS PASSED FOR VENDOR DASHBOARD!")

if __name__ == "__main__":
    asyncio.run(main())

