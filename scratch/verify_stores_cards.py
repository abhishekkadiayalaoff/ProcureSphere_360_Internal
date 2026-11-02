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

        print("Current URL after login:", page.url)
        if "login" in page.url:
            print("Login failed, checking page content...")
            return

        # Navigate to stores dashboard if not directly redirected
        if "/receipts/dashboard" not in page.url:
            await page.goto(f"{BASE_URL}/receipts/dashboard/")
            await page.wait_for_load_state("networkidle")

        print("2. Verifying Stores Dashboard...")
        await page.wait_for_selector(".kpi-card", timeout=8000)

        # Inspect the 5 cards
        cards = await page.query_selector_all(".kpi-card")
        print(f"Found {len(cards)} .kpi-card elements")

        for idx, card in enumerate(cards):
            style = await card.get_attribute("style")
            classes = await card.get_attribute("class")
            text = (await card.inner_text()).replace('\n', ' ')[:60]
            print(f"Card {idx+1}: text='{text}', style='{style}'")

        # Capture Desktop screenshot
        desktop_shot = os.path.join(ARTIFACT_DIR, "stores_dashboard_cards_border.png")
        await page.screenshot(path=desktop_shot, full_page=False)
        print(f"Saved desktop screenshot to {desktop_shot}")

        # Capture close-up of cards
        cards_grid = await page.query_selector(".row.g-3.g-md-4.mb-4")
        if cards_grid:
            cards_shot = os.path.join(ARTIFACT_DIR, "stores_dashboard_cards_zoom.png")
            await cards_grid.screenshot(path=cards_shot)
            print(f"Saved zoom screenshot to {cards_shot}")

        # Test hover state
        await cards[0].hover()
        await page.wait_for_timeout(300)

        # Responsive check: tablet (768px)
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.wait_for_timeout(300)
        tablet_shot = os.path.join(ARTIFACT_DIR, "stores_dashboard_tablet.png")
        await page.screenshot(path=tablet_shot, full_page=False)
        print(f"Saved tablet screenshot to {tablet_shot}")

        await browser.close()
        print("Verification completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
