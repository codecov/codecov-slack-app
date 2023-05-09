import os
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from core.enums import EndpointName
from service_auth.actions import (authenticate_command,
                                  create_new_codecov_access_token,
                                  get_or_create_slack_user,
                                  handle_codecov_public_api_request,
                                  verify_codecov_access_token)
from service_auth.models import Service, SlackUser


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


class TestCreateCodecovAccessToken(TestCase):
    def setUp(self):
        self.slack_user = SlackUser.objects.create(
            username="my_slack_user",
            user_id=12,
            email="",
        )
        Service.objects.create(
            name="my_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )

    def test_create_new_codecov_access_token(self):
        random_uuid = "12345678-1234-5678-1234-567822245672"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": random_uuid}

        with patch("requests.post", return_value=mock_response):
            create_new_codecov_access_token(slack_user=self.slack_user)
            assert self.slack_user.codecov_access_token == random_uuid

    @patch("requests.post")
    def test_create_new_codecov_access_token_no_service(self, mock_post):
        mock_post.return_value = Mock(status_code=401)
        with pytest.raises(Exception) as e:
            create_new_codecov_access_token(slack_user=self.slack_user)

        assert str(e.value) == "Error creating codecov access token"


@patch("service_auth.actions.get_or_create_slack_user")
@patch("service_auth.actions.verify_codecov_access_token")
@patch("service_auth.actions.create_new_codecov_access_token")
@patch("service_auth.actions.view_login_modal")
class TestAuthenticateCommand(TestCase):
    def setUp(self):
        self.slack_user = SlackUser.objects.create(
            username="my_slack_user",
            user_id=12,
            email="",
            codecov_access_token="12345678-1234-5678-1234-567822245672",
        )
        Service.objects.create(
            name="my_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )

        self.client = Mock()
        self.command = {"user_id": "random-userid"}

    def test_successful_authenticate_command(
        self,
        mock_view_modal,
        mock_create_new_access_token,
        mock_verify_access_token,
        mock_get_or_create_slack_user,
    ):
        mock_get_or_create_slack_user.return_value = self.slack_user
        mock_verify_access_token.return_value = True

        authenticate_command(client=self.client, command=self.command)

        mock_get_or_create_slack_user.assert_called_once()
        mock_verify_access_token.assert_called_once_with(self.slack_user)
        mock_create_new_access_token.assert_not_called()
        mock_view_modal.assert_not_called()

    def test_token_not_verified(
        self,
        mock_view_modal,
        mock_create_new_access_token,
        mock_verify_access_token,
        mock_get_or_create_slack_user,
    ):
        mock_get_or_create_slack_user.return_value = self.slack_user
        mock_verify_access_token.return_value = False

        authenticate_command(client=self.client, command=self.command)

        mock_get_or_create_slack_user.assert_called_once()
        mock_verify_access_token.assert_called_once_with(self.slack_user)
        mock_create_new_access_token.assert_called_once_with(self.slack_user)
        mock_view_modal.assert_not_called()

    def test_token_does_not_exist(
        self,
        mock_view_modal,
        mock_create_new_access_token,
        mock_verify_access_token,
        mock_get_or_create_slack_user,
    ):
        self.slack_user.codecov_access_token = None
        mock_get_or_create_slack_user.return_value = self.slack_user
        mock_verify_access_token.return_value = False

        authenticate_command(client=self.client, command=self.command)

        mock_get_or_create_slack_user.assert_called_once()
        mock_verify_access_token.assert_not_called()
        mock_create_new_access_token.assert_not_called()
        mock_view_modal.assert_called_once_with(self.client, self.command)


@patch("requests.get")
class TestHandleCodecovPublicAPI(TestCase):
    def setUp(self):
        self.slack_user = SlackUser.objects.create(
            username="Rula",
            user_id="rula99",
            email="",
        )

    def test_successful_request(self, mock_get):
        params_dict = {
            "username": "rula99",
            "service": "github",
        }

        mock_get.return_value = Mock(status_code=200)
        handle_codecov_public_api_request(
            user_id=self.slack_user.user_id,
            endpoint_name=EndpointName.REPOS,
            service="github",
            optional_params=None,
            params_dict=params_dict,
        )

        mock_get.assert_called_once_with(
            "https://codecov.io/api/github/rula99/repos/",
            headers={"accept": "application/json"},
        )

    def test_404_response(self, mock_get):
        params_dict = {
            "username": "rula99",
            "service": "github",
        }

        mock_get.return_value = Mock(status_code=404)

        with pytest.raises(Exception) as e:
            handle_codecov_public_api_request(
                user_id=self.slack_user.user_id,
                endpoint_name=EndpointName.REPOS,
                service="github",
                optional_params=None,
                params_dict=params_dict,
            )

        assert (
            str(e.value)
            == "Error: Not found.Please use `/codecov login` if you are accessing private data."
        )

    def test_random_endpoint(self, mock_get):
        params_dict = {
            "username": "rula99",
            "service": "github",
        }

        with pytest.raises(Exception) as e:
            handle_codecov_public_api_request(
                user_id=self.slack_user.user_id,
                endpoint_name="random",
                service="github",
                optional_params=None,
                params_dict=params_dict,
            )

        assert str(e.value) == "'random'"  # it's an enum

    def test_codecov_access_token_exists(self, mock_get):
        self.slack_user.codecov_access_token = (
            "12345678-1234-5678-1234-567822245672"
        )
        self.slack_user.save()

        params_dict = {
            "username": "rula99",
            "service": "github",
        }

        mock_get.return_value = Mock(status_code=200)
        handle_codecov_public_api_request(
            user_id=self.slack_user.user_id,
            endpoint_name=EndpointName.REPOS,
            service="github",
            optional_params=None,
            params_dict=params_dict,
        )

        mock_get.assert_called_once_with(
            "https://codecov.io/api/github/rula99/repos/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.slack_user.codecov_access_token}",
            },
        )

    def test_returns_expected_error(self, mock_get):
        params_dict = {
            "username": "rula99",
            "service": "github",
        }

        mock_get.return_value = Mock(status_code=403, text="Forbidden")

        with pytest.raises(Exception) as e:
            handle_codecov_public_api_request(
                user_id=self.slack_user.user_id,
                endpoint_name=EndpointName.REPOS,
                service="github",
                optional_params=None,
                params_dict=params_dict,
            )

        assert str(e.value) == "Error: 403, Forbidden"
