from unittest.mock import Mock

from pytest_mock import MockerFixture

from tests.docs import import_from_path


async def test_api_responses_tutorial_1(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/api-responses-1.py")

    await module.main()


async def test_api_responses_tutorial_2(
    mocker: MockerFixture, mock_print: Mock, mock_start: Mock
) -> None:
    module = import_from_path("docs/tutorials/tutorial-code/api-responses-2.py")

    await module.main()

    mock_print.assert_any_call(
        "Successfully read user data response for user:", "Zendriver"
    )
