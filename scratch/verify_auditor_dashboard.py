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

        print("1. Logging in as auditor@hpe.com...")
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'auditor@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        print("Current URL:", page.url)

        # 2. Check sidebar footnote & footer are gone
        sidebar = await page.query_selector("#auditorSidebar")
        assert sidebar, "Sidebar #auditorSidebar not found!"
        sidebar_text = await sidebar.inner_text()
        
        assert "Immutable Audit Trail" not in sidebar_text, "Error: 'Immutable Audit Trail' found in sidebar!"
        assert "Read-Only Evidence Vault" not in sidebar_text, "Error: 'Read-Only Evidence Vault' found in sidebar!"
        assert "v2026.1" not in sidebar_text, "Error: 'v2026.1' found in sidebar!"
        print("CONFIRMED: All 3 footer elements removed completely from auditor sidebar.")

        # 3. Check Sign Out button count
        signout_btns = await page.query_selector_all('a[href="/logout/"]')
        print(f"Total Sign Out links found: {len(signout_btns)}")
        assert len(signout_btns) == 1, f"Expected exactly 1 Sign Out link on page, got {len(signout_btns)}"
        print("CONFIRMED: Exactly ONE Sign Out button on the entire page, in the top header.")

        # 4. Capture screenshots
        header = await page.query_selector("nav.navbar")
        if header:
            header_shot = os.path.join(ARTIFACT_DIR, "auditor_header_signout_btn.png")
            await header.screenshot(path=header_shot)
            print("Saved header screenshot to:", header_shot)

        sidebar_shot = os.path.join(ARTIFACT_DIR, "auditor_sidebar_clean.png")
        await sidebar.screenshot(path=sidebar_shot)
        print("Saved sidebar screenshot to:", sidebar_shot)

        full_shot = os.path.join(ARTIFACT_DIR, "auditor_dashboard_verified.png")
        await page.screenshot(path=full_shot, full_page=False)
        print("Saved full dashboard screenshot to:", full_shot)

        await browser.close()
        print("Auditor dashboard verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())

