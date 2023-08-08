from logging import Logger
from uuid import uuid4
import pytest

from django.test import TestCase
from django.utils import timezone
from slack_sdk.oauth.installation_store import Bot, Installation

from core.models import SlackBot, SlackInstallation, SlackOAuthState
from core.slack_datastores import (DjangoInstallationStore,
                                   DjangoOAuthStateStore)


class TestDjangoOAuthStateStore(TestCase):
    def setUp(self):
        self.expiration_seconds = 60
        self.logger = Logger("TestDjangoOAuthStateStore")
        self.store = DjangoOAuthStateStore(
            expiration_seconds=self.expiration_seconds,
            logger=self.logger,
        )

    def test_issue(self):
        state = self.store.issue()
        self.assertIsNotNone(state)

        rows = SlackOAuthState.objects.filter(state=state)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.state, state)
        self.assertGreater(row.expire_at, timezone.now())

    def test_consume_existing(self):
        state = self.store.issue()
        result = self.store.consume(state=state)
        self.assertTrue(result)

        rows = SlackOAuthState.objects.filter(state=state)
        self.assertEqual(len(rows), 0)

    def test_consume_expired(self):
        state = self.store.issue()
        row = SlackOAuthState.objects.filter(state=state).first()
        row.expire_at = timezone.now() - timezone.timedelta(seconds=1)
        row.save()

        result = self.store.consume(state=state)
        self.assertFalse(result)

    def test_consume_non_existing(self):
        state = str(uuid4())
        result = self.store.consume(state=state)
        self.assertFalse(result)

        rows = SlackOAuthState.objects.filter(state=state)
        self.assertEqual(len(rows), 0)


class TestDjangoInstallationStore(TestCase):
    def setUp(self):
        self.client_id = str(uuid4())[:32]
        self.logger = Logger(__name__)
        self.store = DjangoInstallationStore(self.client_id, self.logger)
        self.installation = Installation(
            app_id="test-app-id",
            enterprise_id="test-enterprise-id",
            team_id="test-installation-team-id",
            user_id="test-user-id",
            bot_token="test-bot-token",
            bot_id="test-bot-id",
            bot_user_id="test-bot-user-id",
            bot_scopes="test-bot-scope",
            installed_at="20230317",
        )
        self.second_installation = Installation(
            app_id="test-app-id",
            enterprise_id="test-enterprise-id",
            team_id="test-installation-team-id",
            user_id="test-user-id",
            bot_token="test-bot-token",
            bot_id="test-bot-id",
            bot_user_id="other-test-bot-user-id",
            bot_scopes="other-test-bot-scope",
            installed_at="20230317",
        )
        self.bot = Bot(
            app_id="test-app-id",
            enterprise_id="test-enterprise-id",
            team_id="test-bot-team-id",
            bot_token="test-bot-token",
            bot_id="test-bot-id",
            bot_user_id="test-bot-user-id",
            bot_scopes="test-bot-scope",
            installed_at=timezone.now(),
        )

    def test_save(self):
        self.store.save(self.installation)
        row = SlackInstallation.objects.get(client_id=self.store.client_id)
        self.assertEqual(row.enterprise_id, self.installation.enterprise_id)
        self.assertEqual(row.team_id, self.installation.team_id)
        self.assertEqual(row.user_id, self.installation.user_id)

    def test_save_if_exists(self):
        self.store.save(self.installation)

        with pytest.raises(Exception) as e:
            self.store.save(self.second_installation)

        self.assertEqual(
            str(e.value),
            "Codecov Slack App installation for None already exists, please remove app before installing again"
        )

       

    def test_save_bot(self):
        self.store.save_bot(self.bot)
        row = SlackBot.objects.get(client_id=self.store.client_id)
        self.assertEqual(row.enterprise_id, self.bot.enterprise_id)
        self.assertEqual(row.team_id, self.bot.team_id)
        self.assertEqual(row.app_id, self.bot.app_id)

    def test_find_bot_not_found(self):
        row = self.store.find_bot(
            team_id=self.bot.team_id, enterprise_id=self.bot.enterprise_id
        )
        self.assertIsNone(row)

    def test_find_bot(self):
        self.store.save_bot(self.bot)
        row = self.store.find_bot(
            team_id=self.bot.team_id, enterprise_id=self.bot.enterprise_id
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.enterprise_id, self.bot.enterprise_id)
        self.assertEqual(row.team_id, self.bot.team_id)
        self.assertEqual(row.app_id, self.bot.app_id)

    def test_find_installation_not_found(self):
        row = self.store.find_installation(
            team_id=self.bot.team_id, enterprise_id=self.bot.enterprise_id
        )
        self.assertIsNone(row)

    def test_find_installation(self):
        self.store.save(self.installation)
        row = self.store.find_installation(
            team_id=self.installation.team_id,
            enterprise_id=self.installation.enterprise_id,
        )
        self.assertIsNotNone(row)
        self.assertEqual(row.enterprise_id, self.installation.enterprise_id)
        self.assertEqual(row.team_id, self.installation.team_id)
        self.assertEqual(row.app_id, self.installation.app_id)
