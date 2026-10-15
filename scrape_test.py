import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        try:
            await page.goto("https://www.op.gg/summoners/br/Heljufel7-BR1", wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Print a larger chunk of text to see stats
            text = soup.get_text(separator='\n', strip=True)
            with open("opgg_data.txt", "w") as f:
                f.write(text)
            print("Data saved to opgg_data.txt")

            # Try to grab some key divs
            tier = soup.find('div', class_=re.compile(r'tier', re.I))
            if tier: print("Tier info:", tier.text)

            champs = soup.find_all('div', class_=re.compile(r'champion-box', re.I))
            if champs:
                for c in champs[:3]:
                    print("Champion box:", c.text)

        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

asyncio.run(main())
