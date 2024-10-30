import asyncio
from zendriver.core.element import Element

# Constants
CHALLENGE_TITLES = [
    # Cloudflare
    "Just a moment...",
    # DDoS-GUARD
    "DDoS-Guard",
]

async def defeat_cloudflare(tab, headless=False):
    """
    Asynchronously bypasses Cloudflare challenges on the given web page.

    Args:
    ----
    tab: The web page to bypass Cloudflare challenges on.
    headless (bool): Whether the browser is running in headless mode.

    Returns:
    -------
    bool: True if the page was successfully bypassed, False otherwise.
    """
    challenged = False
    while True:
        await tab  # Wait for events to be processed
        if tab.target.title not in CHALLENGE_TITLES:
            return challenged

        if not challenged:
            challenged = True

        try:
            elem = await tab.find(
                "Verify you are human by completing the action below.",
                timeout=3,
            )
        except asyncio.TimeoutError:
            if tab.target.title not in CHALLENGE_TITLES:
                return challenged
            continue

        if elem is None:
            continue

        if not isinstance(elem, Element):
            raise InvalidElementError

        elem = await tab.find("input")
        elem = elem.parent

        # Get the element containing the shadow root
        if isinstance(elem, Element) and elem.shadow_roots:
            inner_elem = Element(elem.shadow_roots[0], tab, elem.tree).children[0]
            if isinstance(inner_elem, Element):
                await inner_elem.mouse_click()
            else:
                if not headless:
                    await pyautogui_click(tab)

        await tab.sleep(1)  # Give some time for the action to take effect

async def pyautogui_click(tab):
    """
    Placeholder for PyAutoGUI click method if needed.
    """
    pass  # Removed PyAutoGUI implementation

class InvalidElementError(Exception):
    pass
