import zendriver as zd


async def test_get_content_gets_html_content(browser: zd.Browser):
    page = await browser.get("https://example.com")
    content = await page.get_content()
    assert content.lower().startswith("<!doctype html>")


async def test_update_target_sets_target_title(browser: zd.Browser):
    page = await browser.get("https://example.com")
    await page.update_target()
    assert page.target
    assert page.target.title == "Example Domain"
