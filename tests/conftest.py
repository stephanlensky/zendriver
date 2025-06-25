import logging
import os
import signal
from enum import Enum
from threading import Event
from typing import AsyncGenerator

import pytest

import zendriver as zd

logger = logging.getLogger(__name__)


class BrowserMode(Enum):
    HEADLESS = "headless"
    HEADFUL = "headful"
    ALL = "all"

    @property
    def fixture_params(self):
        if self == BrowserMode.HEADLESS:
            return [{"headless": True}]
        elif self == BrowserMode.HEADFUL:
            return [{"headless": False}]
        elif self == BrowserMode.ALL:
            return [{"headless": True}, {"headless": False}]


BROWSER_MODE = BrowserMode(os.getenv("ZENDRIVER_TEST_BROWSERS", "all"))

PAUSE_AFTER_TEST = os.getenv("ZENDRIVER_PAUSE_AFTER_TEST", "false") == "true"
NEXT_TEST_EVENT = Event()


@pytest.fixture(params=BROWSER_MODE.fixture_params)
async def browser(request: pytest.FixtureRequest) -> AsyncGenerator[zd.Browser, None]:
    NEXT_TEST_EVENT.clear()
    browser = await zd.start(
        # use wayland for rendering instead of default X11 backend
        browser_args=["--enable-features=UseOzonePlatform", "--ozone-platform=wayland"],
        headless=request.param["headless"],
    )
    browser_pid = browser._process_pid
    assert browser_pid is not None and browser_pid > 0
    yield browser
    if PAUSE_AFTER_TEST:
        logger.info(
            "Pausing after test. Send next test hotkey (default Mod+Return) to continue to next test"
        )
        NEXT_TEST_EVENT.wait()
    await browser.stop()
    assert browser._process_pid is None


# signal handler for starting next test
def handle_next_test(signum, frame):
    if not PAUSE_AFTER_TEST:
        logger.warning(
            "Next test signal received, but ZENDRIVER_PAUSE_AFTER_TEST is not set."
        )
        logger.warning(
            "To enable pausing after each test, set ZENDRIVER_PAUSE_AFTER_TEST=true"
        )
        return

    NEXT_TEST_EVENT.set()


signal.signal(signal.SIGUSR1, handle_next_test)
