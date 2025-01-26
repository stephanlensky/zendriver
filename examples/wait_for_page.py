import asyncio
import zendriver as zd
from zendriver import cdp



async def main():
    browser = await zd.start()
    tab = await browser.get()

    # Enable network tracking
    cdp.network.enable()

    async with tab.expect_response( "https://github.com/") as response:
        # Trigger a request (e.g., click a link or reload)
        await tab.get("https://github.com/")
        await tab.wait_for_load_page(until="complete")
        # todo:: get body
        res = await response.value()
        print(res.request_id)



asyncio.run(main())
