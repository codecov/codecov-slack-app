import os
from unittest.mock import Mock, patch
from django.utils import timezone

import jwt
from django.urls import reverse
from rest_framework.test import APITestCase

from service_auth.models import Service, SlackUser, SlackInstallation
from service_auth.views import GithubCallbackView

slack_user_id_jwt = jwt.encode(
    {"user_id": "random_test_id"},
    os.environ.get("USER_ID_SECRET"),
    algorithm="HS256",
)


class GithubViewTest(APITestCase):
    def setUp(self):
        self.view = GithubCallbackView.as_view()

    def test_with_missing_params(self):
        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {
                "state": slack_user_id_jwt,
            },
        )

        assert response.status_code == 400
        assert response.json() == ["Missing code parameter"]

    @patch("requests.post")
    def test_exchange_access_token_fail(self, mock_post):
        mock_post.return_value = Mock(status_code=400)

        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {"state": slack_user_id_jwt, "code": "test_code"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Error: Could not get access token from GitHub"
        }

    @patch("requests.post")
    def test_no_access_token(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
        )

        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {"state": slack_user_id_jwt, "code": "test_code"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Error: Could not get user info from GitHub"
        }

    @patch("requests.post")
    def test_missing_github_user(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"access_token": "test_token"}),
        )

        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {"state": slack_user_id_jwt, "code": "test_code"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Error: Could not get user info from GitHub"
        }

    @patch("requests.get")
    @patch("requests.post")
    def test_missing_slack_user(self, mock_post, mock_get):
        mock_post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"access_token": "test_token"}),
        )

        mock_get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"id": "test_id", "login": "test_name"}),
        )
        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {"state": slack_user_id_jwt, "code": "test_code"},
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Slack user not found random_test_id"
        }

    @patch("requests.get")
    @patch("requests.post")
    def test_a_successful_flow(self, mock_post, mock_get):
        mock_post.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"access_token": "test_token"}),
        )

        mock_get.return_value = Mock(
            status_code=200,
            json=Mock(return_value={"id": "test_id", "login": "test_name"}),
        )

        installation = SlackInstallation.objects.create(
            bot_token="xoxb-1234567890",
            team_id="random_test_team_id",
            installed_at=timezone.now(),
        )

        self.slack_user = SlackUser.objects.create(
            installation=installation,
            username="slack_user",
            user_id="random_test_id",
            email="",
        )

        response = self.client.get(
            reverse(
                "github-callback",
            ),
            {"state": slack_user_id_jwt, "code": "test_code"},
        )

        assert response.status_code == 302
        assert (
            response.url
            == "https://slack.com/app_redirect?app=292929292929&team=random_test_team_id"
        )
