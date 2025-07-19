from unittest.mock import Mock

from pytest_mock import MockerFixture

from tests.docs import import_from_path


async def test_cdp_tutorial_1(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/cdp-1.py")

    await module.main()


async def test_cdp_tutorial_2(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/cdp-2.py")

    await module.main()

    mock_print.assert_any_call("Console message: log - Button clicked!")
