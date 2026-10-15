import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        import subprocess
        # Start server in background
        proc = subprocess.Popen(["npm", "run", "preview"], cwd="homenagem-heljufel7")
        await asyncio.sleep(5)

        await page.goto("http://localhost:4173")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="homenagem-heljufel7/verification_olaf.png")
        proc.terminate()
        await browser.close()

asyncio.run(run())
