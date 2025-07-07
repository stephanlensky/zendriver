import asyncio

import zendriver as zd
from zendriver import cdp


async def main() -> None:
    browser = await zd.start()
    page = await browser.get(
        "https://slensky.com/zendriver-examples/console.html",
    )

    await page.send(cdp.runtime.enable())

    def console_handler(event: cdp.runtime.ConsoleAPICalled) -> None:
        print(f"Console message: {event.type_} - {event.args}")

    page.add_handler(cdp.runtime.ConsoleAPICalled, console_handler)

    await (await page.select("#myButton")).click()
    await page.wait(1) # Wait for the console messages to be printed

    # Remember to remove handlers to stop listening to console events
    page.remove_handlers(cdp.runtime.ConsoleAPICalled, console_handler)

    await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
