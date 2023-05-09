from django.test import TestCase
from core.resolvers import (
    resolve_service_logout,
)
from unittest.mock import Mock, patch

from service_auth.models import Service, SlackUser


class TestServiceAuthResolvers(TestCase):
    def setUp(self):
        self.slack_user = SlackUser.objects.create(
            username="my_slack_user",
            user_id="user_random_id",
            email="",
            codecov_access_token="12345678-1234-5678-1234-567822245672",
        )
        self. client = Mock()
        self.command = {"user_id": "user_random_id"}
        self.say = Mock()

    @patch("service_auth.actions.get_or_create_slack_user")
    def test_resolve_service_logout_no_active_service(self, mock_get_or_create_slack_user):
        self.client.users_info.return_value = {"user": {"id": "user_random_id"}}

        mock_get_or_create_slack_user.return_value = self.slack_user
        
        resolve_service_logout(client=self.client, command=self.command, say=self.say)
        assert self.say.call_count == 1
        assert self.say.call_args[0] == ('You are not logged in to any service',)

    @patch("service_auth.actions.get_or_create_slack_user")
    def test_resolve_service_logout(self, mock_get_or_create_slack_user):
        self.client.users_info.return_value = {"user": {"id": "user_random_id"}}
        Service.objects.create(
            name="active_service",
            service_username="my_username",
            user=self.slack_user,
            active=True,
        )
        self.slack_user.active = True
        self.slack_user.save()

        mock_get_or_create_slack_user.return_value = self.slack_user
        
        resolve_service_logout(client=self.client, command=self.command, say=self.say)
        assert self.say.call_count == 1
        assert self.say.call_args[0] == ('Successfully logged out of active_service',)

  
