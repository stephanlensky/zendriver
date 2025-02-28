# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Improvements to avoid browser.stop() from causing deadlock or hanging @raycardillo

### Added

### Changed

### Removed

## [0.5.1] - 2025-02-16

### Changed

- Deprecated `zendriver.loop()` function. You should instead use `asyncio` functions directly, for example:

  ```python
  asyncio.run(your_main_method())
  ```

## [0.5.0] - 2025-02-16

### Added

- Add `tab.expect_download` methods to wait for download file @3mora2

## [0.4.3] - 2025-02-11

### Added

- Add logs for Chrome process output on connection failure @stephanlensky

### Changed

- Default and launch changed to use `about:blank` (faster start and less bandwidth) @raycardillo

## [0.4.2] - 2025-02-11

### Fixed

- Multiple Browsers can be created without one affecting the other @raycardillo

## [0.4.1] - 2025-02-09

### Fixed

- Ignore irrelevant `DOM.disable` errors @raycardillo
- Test scripts improved for running on macOS @raycardillo

## [0.4.0] - 2025-02-06

### Added

- Add `tab.expect_request` and `tab.expect_response` methods to wait for a specific request or response @3mora2
- Add `tab.wait_for_ready_state` method for to wait for page to load @3mora2
- Add `tab.remove_handlers` method for removing handlers @khamaileon
- Clean up temporary profiles when `Browser.stop()` is called @barrycarey

## [0.3.1] - 2025-01-28

### Fixed

- Fixed bug in `find`/`find_element_by_text` which caused `ProtocolException` when no results were found @stephanlensky

## [0.3.0] - 2025-01-25

### Fixed

- Added `Tab.set_user_agent()` function for programmatically configuring the user-agent, language, and platform @stephanlensky
- Improved a few type annotations (`Connection.send()` function now returns correctly typed values based on the provided `cdp_obj`) @stephanlensky

## [0.2.3] - 2024-12-14

### Fixed

- Fixed mypy linting errors (attempt 2) @stephanlensky

### Added

- Handle browser process shutdown on 'Failed to connect to browser' @desoul99
- Added configurable browser connection timeout and tries @desoul99

## [0.2.2] - 2024-11-23

### Fixed

- Fix `AttributeError: 'tuple' object has no attribute 'value'` error in `connection.py` when using headless browser, @slimshreydy

## [0.2.1] - 2024-11-23

### Added

- Add automated testing framework! @stephanlensky
  - For now, just a few tests are written, including one to test browserscan.com bot detection
  - In the future, we can expand this test suite further (see [Zendriver#18](https://github.com/stephanlensky/zendriver/issues/18))
- Add return type annotation to `Tab.get_content()` @stephanlensky

### Changed

- Upgraded `websockets` to latest version (`>=14.0`) @yoori @stephanlensky

## [0.2.0] - 2024-11-17

### Changed

- Updated CDP models @stephanlensky

## [0.1.5] - 2024-11-17

### Fixed

- Reverted non-functional fixes for mypy linting errors (oops) @stephanlensky

## [0.1.4] - 2024-11-17

### Fixed

- Fixed a large number of mypy linting errors (should not result in any functional change) @stephanlensky

### Added

- Added `zendriver.__version__` attribute to get current package version at runtime @stephanlensky

## [0.1.3] - 2024-11-12

### Added

- Added support for `DOM.scrollableFlagUpdated` experimental CDP event. @michaellee94

## [0.1.2] - 2024-11-11

### Fixed

- Pinned requirement `websockets<14`, fixing the `AttributeError: 'NoneType' object has no attribute 'closed'` crash which occurs on the latest version of `websockets`. @stephanlensky
- Fixed incorrect `browser.close()` method in examples and documentation -- the correct method is `browser.stop()`. @stephanlensky
- Fixed `atexit` handler to correctly handle async `browser.stop()` method. @stephanlensky

## [0.1.1] - 2024-10-29

### Added

- Support for Python 3.10 and Python 3.11. All versions >=3.10 are now supported. @stephanlensky

## [0.1.0] - 2024-10-20

Initial version, forked from [ultrafunkamsterdam/nodriver@`1bb6003`](https://github.com/ultrafunkamsterdam/nodriver/commit/1bb6003c7f0db4d3ec05fdf3fc8c8e0804260103) with a variety of improvements.

### Fixed

- `Browser.set_all` cookies function now correctly uses provided cookies @ilkecan
- "successfully removed temp profile" message printed on exit is now only shown only when a profile was actually removed. Message is now logged at debug level instead of printed. @mreiden @stephanlensky
- Fix crash on starting browser in headless mode @ilkecan
- Fix `Browser.stop()` method to give the browser instance time to shut down before force killing @stephanlensky
- Many `ruff` lint issues @stephanlensky

### Added

- Support for linting with `ruff` and `mypy`. All `ruff` lints are fixed in the initial release, but many `mypy` issues remain to be fixed at a later date. @stephanlensky
- `py.typed` marker so importing as a library in other packages no longer causes `mypy` errors. @stephanlensky

### Changed

- Project is now built with [`uv`](https://github.com/astral-sh/uv). Automatically install dependencies to a venv with `uv sync`, run commands from the venv with `uv run`, and build the project with `uv build`. See the official [`uv` docs](https://docs.astral.sh/uv/) for more information. @stephanlensky
- Docs migrated from sphinx to [mkdocs-material](https://squidfunk.github.io/mkdocs-material/). @stephanlensky
- `Browser.stop()` is now async (so it must be `await`ed) @stephanlensky

### Removed

- Twitter account creation example @stephanlensky
