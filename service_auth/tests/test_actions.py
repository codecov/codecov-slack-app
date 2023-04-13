from unittest.mock import Mock, patch

import pytest

from service_auth.actions import (_user_info, create_new_codecov_access_token,
                                  get_or_create_slack_user,
                                  verify_codecov_access_token)
from service_auth.models import Service, SlackUser


def test_user_info():
    user_info = {
        "user": {
            "name": "user",
            "profile": {
                "email": "user@example.com",
                "display_name": "Test User",
            },
            "team_id": "12345",
            "is_bot": False,
            "is_owner": True,
            "is_admin": False,
        }
    }
    expected_output = {
        "username": "user",
        "email": "user@example.com",
        "display_name": "Test User",
        "team_id": "12345",
        "is_bot": False,
        "is_owner": True,
        "is_admin": False,
    }
    assert _user_info(user_info) == expected_output


@pytest.mark.django_db
def test_get_or_create_slack_user():
    user_info = {
        "user": {
            "id": "U12345",
            "name": "user",
            "profile": {
                "email": "user@example.com",
                "display_name": "Test User",
            },
            "team_id": "T12345",
            "is_bot": False,
            "is_owner": True,
            "is_admin": False,
        }
    }

    user = get_or_create_slack_user(user_info)
    assert user.user_id == "U12345"
    assert user.username == "user"
    assert user.email == "user@example.com"
    assert user.team_id == "T12345"
    assert user.is_bot is False
    assert user.display_name == "Test User"
    assert user.is_owner is True
    assert user.is_admin is False

    existing_user = get_or_create_slack_user(user_info)
    assert existing_user == user


@pytest.mark.django_db
@patch("requests.get")
def test_verify_codecov_access_token(mock_get):
    slack_user = SlackUser.objects.create(
        username="my_slack_user", user_id=12, email="my_email@example.com"
    )
    Service.objects.create(
        name="my_service",
        service_username="my_username",
        user=slack_user,
        active=True,
    )

    mock_get.return_value = Mock(status_code=200)
    assert verify_codecov_access_token(slack_user) == True

    mock_get.return_value = Mock(status_code=401)
    assert verify_codecov_access_token(slack_user) == False


@pytest.mark.django_db
def test_create_new_codecov_access_token():
    slack_user = SlackUser.objects.create(
        username="my_slack_user",
        user_id=12,
        email="",
    )
    Service.objects.create(
        name="my_service",
        service_username="my_username",
        user=slack_user,
        active=True,
    )

    random_uuid = "12345678-1234-5678-1234-567822245672"

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"token": random_uuid}

    with patch("requests.post", return_value=mock_response):
        create_new_codecov_access_token(slack_user)
        assert slack_user.codecov_access_token == random_uuid


@pytest.mark.django_db
@patch("requests.post")
def test_create_new_codecov_access_token_no_service(mock_post):
    slack_user = SlackUser.objects.create(
        username="my_slack_user",
        user_id=12,
        email="",
    )
    Service.objects.create(
        name="my_service",
        service_username="my_username",
        user=slack_user,
        active=True,
    )

    mock_post.return_value = Mock(status_code=401)
    with pytest.raises(Exception) as e:
        create_new_codecov_access_token(slack_user)

    assert str(e.value) == "Error creating codecov access token"
