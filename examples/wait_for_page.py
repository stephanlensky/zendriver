import asyncio
import zendriver as zd


async def main():
    browser = await zd.start()
    tab = await browser.get()

    async with tab.expect_request( "https://github.com/") as request_info:
        async with tab.expect_response("https://github.githubassets.com/assets/**") as response_info:
            await tab.get("https://github.com/")
            await tab.wait_for_load_page(until="complete")

            req = await request_info.value
            print(req.request_id)

            res = await response_info.value
            print(res.request_id)


if __name__ == "__main__":
    asyncio.run(main())
