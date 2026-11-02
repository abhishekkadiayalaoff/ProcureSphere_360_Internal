import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page()
        await page.goto('http://127.0.0.1:8000/login/')
        await page.fill('#email', 'procmgr@hpe.com')
        await page.fill('#password', 'Password123!')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state('networkidle')
        await page.goto('http://127.0.0.1:8000/manager/')
        print("Loaded /manager/, current URL:", page.url)
        await page.wait_for_timeout(1000)
        
        container = await page.query_selector('#kpiCardsContainer')
        if container:
            cls = await container.get_attribute('class')
            print('kpiCardsContainer class:', cls)
            cards = await container.query_selector_all('.card')
            print('cards in container:', len(cards))
            for i, c in enumerate(cards):
                style = await c.get_attribute('style')
                text = (await c.inner_text()).replace('\n', ' ')
                print(f"Card {i+1}: style='{style}', text='{text[:60]}'")
        else:
            print('No #kpiCardsContainer found!')
        await b.close()

asyncio.run(run())

