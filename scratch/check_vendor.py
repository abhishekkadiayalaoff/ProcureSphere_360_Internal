import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{BASE_URL}/login/")
        await page.fill('#email', 'vendoruser@cisco.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        dest = os.path.join(ARTIFACT_DIR, "vendor_dashboard_untouched5.png")
        await page.screenshot(path=dest, full_page=False)
        print("Vendor screenshot saved to", dest)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

