import asyncio

import pytest

import zendriver as zd
from tests.sample_data import sample_file


async def test_set_user_agent_sets_navigator_values(browser: zd.Browser):
    tab = browser.main_tab

    await tab.set_user_agent(
        "Test user agent", accept_language="testLang", platform="TestPlatform"
    )

    navigator_user_agent = await tab.evaluate("navigator.userAgent")
    navigator_language = await tab.evaluate("navigator.language")
    navigator_platform = await tab.evaluate("navigator.platform")
    assert navigator_user_agent == "Test user agent"
    assert navigator_language == "testLang"
    assert navigator_platform == "TestPlatform"


async def test_set_user_agent_defaults_existing_user_agent(browser: zd.Browser):
    tab = browser.main_tab
    existing_user_agent = await tab.evaluate("navigator.userAgent")

    await tab.set_user_agent(accept_language="testLang")

    navigator_user_agent = await tab.evaluate("navigator.userAgent")
    navigator_language = await tab.evaluate("navigator.language")
    assert navigator_user_agent == existing_user_agent
    assert navigator_language == "testLang"


async def test_find_finds_element_by_text(browser: zd.Browser):
    tab = await browser.get(sample_file("groceries.html"))

    result = await tab.find("Apples")

    assert result is not None
    assert result.tag == "li"
    assert result.text == "Apples"


async def test_find_times_out_if_element_not_found(browser: zd.Browser):
    tab = await browser.get(sample_file("groceries.html"))

    with pytest.raises(asyncio.TimeoutError):
        await tab.find("Clothes", timeout=1)


async def test_select(browser: zd.Browser):
    tab = await browser.get(sample_file("groceries.html"))

    result = await tab.select("li[aria-label='Apples (42)']")

    assert result is not None
    assert result.tag == "li"
    assert result.text == "Apples"
