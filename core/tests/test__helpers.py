import pytest

from core.enums import EndpointName
from core.helpers import (extract_command_params, extract_optional_params,
                          format_nested_keys, validate_comparison_params,
                          validate_service)


def test_validate_service():
    assert validate_service("gh") == "github"

    with pytest.raises(ValueError):
        validate_service("invalid_gh")


def test_extract_command_params():
    command_name = EndpointName.OWNER
    assert extract_command_params(
        command={"text": "/codecov owner username=rula service=gh"},
        command_name=command_name,
    ) == {"username": "rula", "service": "gh"}

    with pytest.raises(ValueError) as e:
        extract_command_params(
            command={"text": "/codecov owner service=gh"},
            command_name=command_name,
        )

    assert str(e.value) == "Missing required parameter username"


def test_extract_optional_params():
    assert (
        extract_optional_params(
            params_dict={"username": "rula", "service": "gh"},
            command_name=EndpointName.OWNER,
        )
        == {}
    )

    assert extract_optional_params(
        params_dict={"username": "rula", "service": "gh", "active": True},
        command_name=EndpointName.REPOS,
    ) == {"active": True}


@pytest.fixture
def data():
    return {
        "results": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
            },
            {
                "id": 2,
                "name": "Bob",
                "email": "bob@example.com",
            },
        ]
    }


def test_format_nested_keys(data):
    expected_output = (
        "*Id*: 1\n*Name*: Alice\n*Email*: alice@example.com\n------------------\n"
        + "*Id*: 2\n*Name*: Bob\n*Email*: bob@example.com\n------------------\n"
    )
    assert format_nested_keys(data, "") == expected_output


def test_validate_comparison_params():
    with pytest.raises(Exception) as e:
        validate_comparison_params(
            params_dict={"username": "rula", "service": "gh"},
        )

    assert (
        str(e.value)
        == "Comparison requires both a base and head parameter or a pullid parameter"
    )

    assert (
        validate_comparison_params(
            params_dict={"base": "rula", "head": "gh", "pullid": 1},
        )
        == None
    )
