import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\windows10\.gemini\antigravity\brain\a551de30-c6e9-45bc-936f-eb80bbe1d733"
BASE_URL = "http://127.0.0.1:8000"

async def verify_manager(browser):
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    print("\n--- Verifying Procurement Manager ---")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('#email', 'procmgr@hpe.com')
    await page.fill('#password', 'Password123!')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    await page.goto(f"{BASE_URL}/manager/")
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(1000)

    # Screenshot dashboard
    await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_procmgr_dashboard.png"))

    # Check 4 KPI cards
    cards = await page.query_selector_all('#kpiCardsContainer .card')
    print(f"Proc Manager KPI cards found: {len(cards)}")
    assert len(cards) == 4, f"Expected 4 KPI cards, found {len(cards)}"
    
    # Check sidebar footnote absence
    body_text = await page.inner_text('body')
    assert "RBAC Backend Enforced" not in body_text, "Footnote 'RBAC Backend Enforced' still present!"
    print("Proc Manager sidebar footnote removed verified!")
    print("Proc Manager verified!")
    await context.close()

async def verify_stores(browser):
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    print("\n--- Verifying Stores Dashboard ---")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('#email', 'receiver@hpe.com')
    await page.fill('#password', 'Password123!')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    await page.goto(f"{BASE_URL}/receipts/dashboard/")
    await page.wait_for_load_state("networkidle")

    # Screenshot
    await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_stores_dashboard.png"))

    # Check sidebar footnote absence
    body_text = await page.inner_text('body')
    assert "Physical Intake • Quality Verified" not in body_text, "Stores footnote still present!"
    print("Stores sidebar footnote removed verified!")
    print("Stores verified!")
    await context.close()

async def verify_legal(browser):
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    print("\n--- Verifying Legal Dashboard ---")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('#email', 'legal@hpe.com')
    await page.fill('#password', 'Password123!')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    await page.goto(f"{BASE_URL}/contracts/dashboard/")
    await page.wait_for_load_state("networkidle")

    # Screenshot
    await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_legal_dashboard.png"))

    body_text = await page.inner_text('body')
    assert "SLA Enforcement • Legal Compliance" not in body_text, "Legal footnote still present!"
    print("Legal sidebar footnote removed verified!")
    print("Legal verified!")
    await context.close()

async def verify_auditor(browser):
    context = await browser.new_context(viewport={"width": 1440, "height": 900})
    page = await context.new_page()
    print("\n--- Verifying Auditor Dashboard ---")
    await page.goto(f"{BASE_URL}/login/")
    await page.fill('#email', 'auditor@hpe.com')
    await page.fill('#password', 'Password123!')
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    await page.goto(f"{BASE_URL}/audit/dashboard/")
    await page.wait_for_load_state("networkidle")

    # Screenshot
    await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_auditor_dashboard.png"))

    body_text = await page.inner_text('body')
    assert "Immutable Audit Trail • WORM Compliant" not in body_text, "Auditor footnote still present!"
    assert "Read-Only Evidence Vault" not in body_text, "Auditor vault footnote still present!"
    print("Auditor sidebar bottom items removed verified!")
    print("Auditor verified!")
    await context.close()

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await verify_manager(browser)
        await verify_stores(browser)
        await verify_legal(browser)
        await verify_auditor(browser)
        await browser.close()
        print("\nALL SPECIFIC DASHBOARD CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(main())
