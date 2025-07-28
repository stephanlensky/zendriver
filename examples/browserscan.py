import asyncio

import zendriver as zd


async def main() -> None:
    browser = await zd.start()
    page = await browser.get("https://www.browserscan.net/bot-detection")
    await page.save_screenshot("browserscan.png")
    await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
