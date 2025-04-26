import pytest
from pytest_mock import MockerFixture

import zendriver as zd
from tests.conftest import CreateBrowser


async def test_connection_error_raises_exception_and_logs_stderr(
    create_browser: type[CreateBrowser],
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    mocker.patch(
        "zendriver.core.browser.Browser.test_connection",
        return_value=False,
    )
    with caplog.at_level("INFO"):
        with pytest.raises(Exception):
            async with create_browser(
                browser_connection_max_tries=1, browser_connection_timeout=0.1
            ) as _:
                pass
    assert "Browser stderr" in caplog.text


async def test_get_content_gets_html_content(browser: zd.Browser):
    page = await browser.get("https://example.com")
    content = await page.get_content()
    assert content.lower().startswith("<!doctype html>")


async def test_update_target_sets_target_title(browser: zd.Browser):
    page = await browser.get("https://example.com")
    await page.update_target()
    assert page.target
    assert page.target.title == "Example Domain"
