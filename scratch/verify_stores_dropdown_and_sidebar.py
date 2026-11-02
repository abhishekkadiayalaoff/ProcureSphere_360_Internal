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

        print("1. Logging in as receiver@hpe.com...")
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'receiver@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        print("Navigating to stores dashboard...")
        if "/receipts/dashboard" not in page.url:
            await page.goto(f"{BASE_URL}/receipts/dashboard/")
            await page.wait_for_load_state("networkidle")

        # 2. Check sidebar for "Physical Intake"
        page_text = await page.content()
        assert "Physical Intake" not in page_text, "Error: 'Physical Intake' still found on page!"
        print("CONFIRMED: 'Physical Intake • Quality Verified' is completely removed from sidebar.")

        # 3. Click avatar dropdown button
        dropdown_btn = await page.query_selector(".stores-topbar .dropdown button")
        assert dropdown_btn, "Dropdown button not found!"
        await dropdown_btn.click()
        await page.wait_for_timeout(400)

        # Inspect dropdown items
        menu_items = await page.query_selector_all(".stores-topbar .dropdown-menu .dropdown-item")
        print(f"Dropdown item count: {len(menu_items)}")
        for item in menu_items:
            print("  Item text:", (await item.inner_text()).strip())
        assert len(menu_items) == 1, f"Expected exactly 1 item in dropdown, got {len(menu_items)}"

        # Capture screenshot with dropdown opened
        dropdown_shot = os.path.join(ARTIFACT_DIR, "stores_dropdown_signout_only.png")
        await page.screenshot(path=dropdown_shot, full_page=False)
        print("Saved dropdown screenshot to:", dropdown_shot)

        # Capture sidebar bottom screenshot
        sidebar = await page.query_selector("#storesSidebar")
        if sidebar:
            sidebar_shot = os.path.join(ARTIFACT_DIR, "stores_sidebar_clean.png")
            await sidebar.screenshot(path=sidebar_shot)
            print("Saved sidebar screenshot to:", sidebar_shot)

        await browser.close()
        print("All checks passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())

