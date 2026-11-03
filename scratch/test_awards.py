from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://127.0.0.1:8000/login/')
    page.fill('input[type="email"]', 'procmgr@hpe.com')
    page.fill('input[name="password"]', 'Password123!')
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')
    print('Logged in URL:', page.url)
    
    page.goto('http://127.0.0.1:8000/manager/awards/')
    page.wait_for_load_state('networkidle')
    print('Awards page URL:', page.url)
    print('Awards page Title:', page.title())
    print('Logout elements count:', page.locator('a[href*="/logout/"]').count())
    print('Content preview:', page.content()[:300])
    browser.close()

