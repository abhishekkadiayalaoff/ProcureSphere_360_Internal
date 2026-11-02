import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Test Stores Dashboard
        context1 = await browser.new_context(viewport={"width": 1440, "height": 900})
        page1 = await context1.new_page()
        print("Testing Stores Dashboard...")
        await page1.goto(f"{BASE_URL}/login/")
        await page1.fill('#email', 'receiver@hpe.com')
        await page1.fill('#password', 'Password123!')
        await page1.click('button[type="submit"]')
        await page1.wait_for_load_state("networkidle")
        if "/receipts/dashboard" not in page1.url:
            await page1.goto(f"{BASE_URL}/receipts/dashboard/")
            await page1.wait_for_load_state("networkidle")

        signout_link1 = await page1.query_selector('a[href="/logout/"]')
        assert signout_link1, "Stores dashboard Sign Out button not found!"
        btn_text1 = (await signout_link1.inner_text()).strip()
        print(f"Stores Sign Out button text: '{btn_text1}'")
        
        # Header zoom screenshot
        header1 = await page1.query_selector("nav.stores-topbar")
        if header1:
            dest1 = os.path.join(ARTIFACT_DIR, "stores_header_signout_btn.png")
            await header1.screenshot(path=dest1)
            print("Saved stores header screenshot to:", dest1)
        
        full_dest1 = os.path.join(ARTIFACT_DIR, "stores_dashboard_with_signout_btn.png")
        await page1.screenshot(path=full_dest1, full_page=False)
        print("Saved full stores dashboard screenshot to:", full_dest1)
        await context1.close()

        # 2. Test Vendor Dashboard
        context2 = await browser.new_context(viewport={"width": 1440, "height": 900})
        page2 = await context2.new_page()
        print("\nTesting Vendor Dashboard...")
        await page2.goto(f"{BASE_URL}/login/")
        await page2.fill('#email', 'vendoruser@cisco.com')
        await page2.fill('#password', 'Password123!')
        await page2.click('button[type="submit"]')
        await page2.wait_for_load_state("networkidle")

        signout_link2 = await page2.query_selector('a[href="/logout/"]')
        assert signout_link2, "Vendor dashboard Sign Out button not found!"
        btn_text2 = (await signout_link2.inner_text()).strip()
        print(f"Vendor Sign Out button text: '{btn_text2}'")
        
        header2 = await page2.query_selector("nav.navbar")
        if header2:
            dest2 = os.path.join(ARTIFACT_DIR, "vendor_header_signout_btn.png")
            await header2.screenshot(path=dest2)
            print("Saved vendor header screenshot to:", dest2)

        full_dest2 = os.path.join(ARTIFACT_DIR, "vendor_dashboard_with_signout_btn.png")
        await page2.screenshot(path=full_dest2, full_page=False)
        print("Saved full vendor dashboard screenshot to:", full_dest2)
        await context2.close()

        await browser.close()
        print("\nAll verifications succeeded!")

if __name__ == "__main__":
    asyncio.run(main())

