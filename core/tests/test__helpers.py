from unittest.mock import Mock, patch

import pytest
from slack_sdk.models.blocks import ButtonElement, DividerBlock, SectionBlock

from core.enums import EndpointName
from core.helpers import (channel_exists, extract_command_params,
                          extract_optional_params, format_comparison,
                          format_nested_keys, validate_comparison_params,
                          validate_notification_params, validate_service)


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


def test_validate_notification_params():
    with pytest.raises(ValueError) as e:
        validate_notification_params(
            comparison=None,
            repo="rula",
            owner="gh",
        )

    assert (
        str(e.value)
        == "Comparison requires a repository, owner and comparison parameter"
    )

    assert (
        validate_notification_params(
            comparison="rula",
            repo="rula",
            owner="gh",
        )
        == None
    )


def test_channel_exists():
    client = Mock()
    client.conversations_list.return_value = {
        "channels": [
            {"id": "C01B2AB8K3A", "name": "general"},
            {"id": "C01B2AB8K3B", "name": "random"},
        ]
    }
    assert channel_exists(client, "invalid") == False
    assert channel_exists(client, "C01B2AB8K3A") == True


def test_format_comparison():
    comparison = {
        "head_commit": {
            "commitid": "1234567890abcdef",
            "branch": "main",
            "message": "Update README",
            "author": "John Doe",
            "timestamp": "2023-05-31T12:34:56",
            "ci_passed": True,
            "totals": {"C": 0, "M": 0, "N": 0},
            "pull": 123,
        },
        "head_totals_c": 0,
    }

    expected_blocks = [
        DividerBlock(),
        SectionBlock(
            text="*Head Commit* _1234567_\n"
            "*ID:* 1234567890abcdef\n"
            "*Branch:* main\n"
            "*Message:* Update README\n"
            "*Author:* John Doe\n"
            "*Timestamp:* 2023-05-31T12:34:56\n"
            "*CI Passed:* ✅\n"
        ),
        DividerBlock(),
        SectionBlock(
            text="ℹ️ You can use `/codecov compare` to get the full comparison. Use `/codecov help` to know more."
        ),
    ]

    assert format_comparison(comparison) == expected_blocks
