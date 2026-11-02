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

        print("--- Testing Procurement Manager Dashboard (Watchlist Table) ---")
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'procmgr@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")

        await page.goto(f"{BASE_URL}/manager/")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Check rows in #dashWatchlistBody
        rows = await page.query_selector_all('#dashWatchlistBody tr')
        print(f"Watchlist rows found: {len(rows)}")
        assert len(rows) > 0, "No rows found in watchlist table"

        # Check that none of the rows have border-danger or red border class
        for i, row in enumerate(rows):
            cls = await row.get_attribute('class') or ''
            print(f"Row {i+1} class: '{cls}'")
            assert 'border-danger' not in cls, f"Row {i+1} still has border-danger class: {cls}"
            assert 'bg-danger-subtle' not in cls, f"Row {i+1} still has bg-danger-subtle class: {cls}"

        # Screenshot the watchlist card
        table_card = await page.query_selector('table.table')
        if table_card:
            card_container = await page.evaluate_handle('el => el.closest(".card")', table_card)
            if card_container:
                shot_path = os.path.join(ARTIFACT_DIR, "proc_mgr_watchlist_no_red_lines.png")
                await card_container.as_element().screenshot(path=shot_path)
                print(f"Saved watchlist screenshot: {shot_path}")

        # Full page screenshot
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "proc_mgr_dashboard_no_red_lines.png"))
        print("Saved full page screenshot: proc_mgr_dashboard_no_red_lines.png")

        await browser.close()
        print("VERIFICATION COMPLETED SUCCESSFULLY: Red lines are completely gone!")

if __name__ == "__main__":
    asyncio.run(main())

