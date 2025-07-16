import pytest
import threading
import socket
import time

import zendriver as zd
import http.server
import socketserver
from zendriver import SpecialKeys, KeyModifiers, KeyEvents


def find_free_port():
    """Find a free port to avoid conflicts."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


@pytest.fixture(scope="module")
def http_server():
    """Start HTTP server once for all tests in this module."""
    PORT = find_free_port()
    Handler = http.server.SimpleHTTPRequestHandler

    try:
        # Create and start server
        httpd = socketserver.TCPServer(("", PORT), Handler)
        server_thread = threading.Thread(target=lambda: httpd.serve_forever())
        server_thread.daemon = True
        server_thread.start()

        print(f"Server started at http://localhost:{PORT}")

        time.sleep(1)

        yield {"httpd": httpd, "port": PORT, "thread": server_thread}

    finally:
        # Cleanup
        print("Shutting down HTTP server...")
        httpd.shutdown()
        httpd.server_close()
        server_thread.join(timeout=5)
        print("Server shut down.")


async def test_visible_events(browser: zd.Browser, http_server):
    """Test keyboard events with contenteditable div."""
    PORT = http_server["port"]

    try:
        # Open the page
        main_page = await browser.get(f"http://localhost:{PORT}/tests/keys/simple_editor.html")

        text_part = await main_page.find('//*[@id="editor"]')

        await text_part.mouse_click("left")
        await main_page.sleep(1)  # give some time to focus the text part
        await text_part.send_keys("Hello, world!")

        payloads = KeyEvents.from_mixed_input(
            [
                " This is another sentence",
                SpecialKeys.ENTER,
                ("a", KeyModifiers.Ctrl),
                ("c", KeyModifiers.Ctrl),
                SpecialKeys.ARROW_UP,
                ("v", KeyModifiers.Ctrl),
                " This is pasted text. 👍",
            ]
        )

        await text_part.send_keys(payloads)
        check_part = await main_page.find('//*[@id="editor"]')
        assert len(check_part.children) == 4, "Expected 4 children after operations"

        expected_output = [
            "Hello, world! This is another sentence",
            "<div>&nbsp;This is pasted text. 👍</div>",
            "Hello, world! This is another sentence",
            "<div><br></div>",
        ]

        for expected, actual_text in zip(expected_output, check_part.children):
            actual_html = await actual_text.get_html()
            assert (
                actual_html == expected
            ), f"Expected '{expected}', got '{actual_html}'"

    except Exception as e:
        print(f"An error occurred: {e}")
        pytest.fail(f"Test failed with exception: {e}")
        
        
async def test_escape_key_popup(browser: zd.Browser, http_server):
    """Test escape key functionality to close a popup."""
    PORT = http_server["port"]

    main_page = await browser.get(f"http://localhost:{PORT}/tests/keys/special_key_detector.html")
    
    status_check = await main_page.find('//*[@id="status"]')
    assert status_check.text == "Ready - Click button to open popup", "There is something wrong with the page"

    button = await main_page.find('//*[@id="popUpButton"]')
    await button.mouse_click("left")
    
    await status_check
    assert status_check.text == "popUp is OPEN - Press Escape to close", "Popup did not open correctly"
    
    pop_up = await main_page.find('//*[@id="mainpage"]/div')
    await pop_up.send_keys(SpecialKeys.ESCAPE)

    await status_check
    assert status_check.text == "popUp is CLOSED - Click button to open again", "Popup did not close correctly"
