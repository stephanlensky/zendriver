import asyncio

import zendriver as zd
from zendriver import cdp


async def main() -> None:
    browser = await zd.start()
    page = await browser.get(
        "https://slensky.com/zendriver-examples/console.html",
    )

    await page.send(cdp.runtime.enable())

    await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
