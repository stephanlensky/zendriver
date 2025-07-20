from unittest.mock import Mock

from pytest_mock import MockerFixture

from tests.docs import import_from_path


async def test_account_creation_tutorial_1(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/account-creation-1.py")

    await module.main()  # just loading the page


async def test_account_creation_tutorial_2(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/account-creation-2.py")

    await module.main()

    mock_print.assert_has_calls(
        [
            mocker.call("Login successful"),
        ]
    )
