from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from core.models import Notification, SlackInstallation
from core.views import NotificationView

codecov_internal_token = "random_internal_token"


class NotificationViewSetTests(APITestCase):
    def setUp(self):
        installation = SlackInstallation.objects.create(
            bot_token="random_bot_token",
            installed_at=timezone.now(),
        )
        self.notification = Notification.objects.create(
            repo="random-repo",
            owner="random-owner",
            installation=installation,
            channels=["random-channel"],
        )
        self.data = {
            "owner": self.notification.owner,
            "repository": self.notification.repo,
            "comparison": "random-comparison",
        }
        self.view = NotificationView.as_view()

    def test_post_notifications_missing_headers(self):
        response = self.client.post(
            reverse(
                "notify",
            )
        )

        assert response.status_code == 401
        assert response.data == {
            "detail": "Authentication credentials were not provided."
        }

    def test_post_notifications_with_invalid_token(self):
        response = self.client.post(
            reverse(
                "notify",
            ),
            HTTP_AUTHORIZATION=f"Bearer random_token",
            data=self.data,
        )
        assert response.status_code == 401
        assert response.data == {"detail": "Invalid token."}

    def test_post_notifications_with_missing_params(self):
        with pytest.raises(ValueError) as e:
            self.client.post(
                reverse(
                    "notify",
                ),
                HTTP_AUTHORIZATION=f"Bearer {codecov_internal_token}",
                data={
                    "repository": self.notification.repo,
                },
            )

        assert (
            str(e.value)
            == "Comparison requires a repository, owner and comparison parameter"
        )

    def test_post_notifications_does_not_exist(self):
        response = self.client.post(
            reverse(
                "notify",
            ),
            HTTP_AUTHORIZATION=f"Bearer {codecov_internal_token}",
            data={
                "owner": "diff-owner",
                "repository": "diff-repo",
                "comparison": "diff-comparison",
            },
        )

        assert response.status_code == 404
        assert response.data == {"detail": "No notifications found"}

    @patch("core.views.WebClient")
    @patch("core.views.SlackApiError")
    @patch("core.views.channel_exists")
    def test_post_notifications_success(
        self, mock_web_client, mock_channel_exists, mock_slack_api_error
    ):
        mock_channel_exists.return_value = True
        mock_web_client.return_value.chat_postMessage.return_value = True
        mock_slack_api_error.return_value.response = {"ok": True}

        response = self.client.post(
            reverse(
                "notify",
            ),
            data=self.data,
            HTTP_AUTHORIZATION=f"Bearer {codecov_internal_token}",
        )

        assert response.status_code == 200


class TestHealth(APITestCase):
    def test_health(self):
        url = reverse("health")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"Codecov Slack App is live!")
