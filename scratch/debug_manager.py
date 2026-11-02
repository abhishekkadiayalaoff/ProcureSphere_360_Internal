import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page()
        page.on("console", lambda msg: print("PAGE LOG:", msg.text))
        await page.goto('http://127.0.0.1:8000/login/')
        await page.fill('#email', 'procmgr@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')
        await page.goto('http://127.0.0.1:8000/manager/dashboard/')
        print("Loaded manager/dashboard/, current URL:", page.url)
        await page.wait_for_timeout(2000)
        
        container = await page.query_selector('#kpiCardsContainer')
        if container:
            cls = await container.get_attribute('class')
            print('kpiCardsContainer class:', cls)
            cards = await container.query_selector_all('.card')
            print('cards in container:', len(cards))
        else:
            print('No #kpiCardsContainer found!')
            h1 = await page.query_selector('h1, h2, h3')
            if h1:
                print('Heading:', await h1.inner_text())
        await b.close()

asyncio.run(run())

