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

        print("1. Logging in as legal@hpe.com...")
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'legal@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        print("Current URL:", page.url)
        if "/contracts/dashboard" not in page.url:
            await page.goto(f"{BASE_URL}/contracts/dashboard/")
            await page.wait_for_load_state("networkidle")

        # 2. Check sidebar footnote is gone
        content = await page.content()
        assert "SLA Enforcement" not in content, "Error: 'SLA Enforcement' still found on page!"
        print("CONFIRMED: 'SLA Enforcement • Legal Compliance' is completely removed from sidebar.")

        # 3. Check Sign Out button
        signout_btn = await page.query_selector('a[href="/logout/"]')
        assert signout_btn, "Sign Out button not found in header!"
        print("Sign Out button text:", (await signout_btn.inner_text()).strip())

        # 4. Check the 4 KPI cards
        cards = await page.query_selector_all(".kpi-card")
        print(f"Found {len(cards)} KPI cards")
        assert len(cards) >= 4, f"Expected 4 cards, found {len(cards)}"

        for idx, card in enumerate(cards[:4]):
            style = await card.get_attribute("style")
            text = (await card.inner_text()).replace('\n', ' ')[:60]
            print(f"Card {idx+1}: text='{text}', style='{style}'")

        # 5. Capture screenshots
        header = await page.query_selector("nav.navbar")
        if header:
            header_shot = os.path.join(ARTIFACT_DIR, "legal_header_signout_btn.png")
            await header.screenshot(path=header_shot)
            print("Saved header screenshot to:", header_shot)

        sidebar = await page.query_selector("#legalSidebar")
        if sidebar:
            sidebar_shot = os.path.join(ARTIFACT_DIR, "legal_sidebar_clean.png")
            await sidebar.screenshot(path=sidebar_shot)
            print("Saved sidebar screenshot to:", sidebar_shot)

        cards_grid = await page.query_selector(".row.g-3.g-md-4.mb-4")
        if cards_grid:
            cards_shot = os.path.join(ARTIFACT_DIR, "legal_dashboard_cards_zoom.png")
            await cards_grid.screenshot(path=cards_shot)
            print("Saved cards zoom screenshot to:", cards_shot)

        full_shot = os.path.join(ARTIFACT_DIR, "legal_dashboard_cards_border.png")
        await page.screenshot(path=full_shot, full_page=False)
        print("Saved full dashboard screenshot to:", full_shot)

        await browser.close()
        print("Legal dashboard verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())

