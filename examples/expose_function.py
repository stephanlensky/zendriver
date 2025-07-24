import asyncio
import hashlib

import zendriver as zd


async def main():
    async def sha256(text):
        m = hashlib.sha256()
        m.update(bytes(text, "utf8"))
        return m.hexdigest()

    async with await zd.start(headless=False) as browser:
        page = browser.main_tab
        await page.expose_function("sha256", sha256)

        await page.set_content("""
                <script>
                  async function onClick() {
                    document.querySelector('div#secret').textContent = await window.sha256('zendriver');
                  }
                </script>
                <button onclick="onClick()">Click me</button>
                <div id="secret"></div>
            """)


if __name__ == "__main__":
    asyncio.run(main())
