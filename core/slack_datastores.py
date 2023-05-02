# ----------------------
# Bolt store implementations
# ----------------------

import datetime
from logging import Logger
from typing import Optional
from uuid import uuid4

from django.db.models import F
from django.utils import timezone
from django.utils.timezone import is_naive, make_aware
from slack_sdk.oauth import InstallationStore, OAuthStateStore
from slack_sdk.oauth.installation_store import Bot, Installation

from core.models import SlackBot, SlackInstallation, SlackOAuthState


class DjangoInstallationStore(InstallationStore):
    client_id: str

    def __init__(
        self,
        client_id: str,
        logger: Logger,
    ):
        self.client_id = client_id
        self._logger = logger

    def save(self, installation: Installation):
        bot_token_expires_at = installation.bot_token_expires_at
        user_token_expires_at = installation.user_token_expires_at
        installed_at = installation.installed_at

        if installed_at is not None:
            installed_at = datetime.datetime.fromtimestamp(installed_at)
            if is_naive(installed_at):
                installed_at = make_aware(installed_at)

        if bot_token_expires_at is not None:
            bot_token_expires_at = datetime.datetime.fromtimestamp(
                bot_token_expires_at
            )
            if is_naive(bot_token_expires_at):
                bot_token_expires_at = make_aware(bot_token_expires_at)

        if user_token_expires_at is not None:
            user_token_expires_at = datetime.datetime.fromtimestamp(
                user_token_expires_at
            )
            if is_naive(user_token_expires_at):
                user_token_expires_at = make_aware(user_token_expires_at)

        slack_installation = SlackInstallation.objects.filter(
            client_id=self.client_id,
            enterprise_id=installation.enterprise_id,
            team_id=installation.team_id,
            installed_at=installed_at,
        ).first()

        if slack_installation is None:
            slack_installation = SlackInstallation()

        slack_installation.client_id = self.client_id
        slack_installation.app_id = installation.app_id
        slack_installation.enterprise_id = installation.enterprise_id
        slack_installation.enterprise_name = installation.enterprise_name
        slack_installation.enterprise_url = installation.enterprise_url
        slack_installation.team_id = installation.team_id
        slack_installation.team_name = installation.team_name
        slack_installation.bot_token = installation.bot_token
        slack_installation.bot_refresh_token = installation.bot_refresh_token
        slack_installation.bot_token_expires_at = bot_token_expires_at
        slack_installation.bot_id = installation.bot_id
        slack_installation.bot_user_id = installation.bot_user_id
        slack_installation.bot_scopes = installation.bot_scopes
        slack_installation.user_id = installation.user_id
        slack_installation.user_token = installation.user_token
        slack_installation.user_refresh_token = installation.user_refresh_token
        slack_installation.user_token_expires_at = user_token_expires_at
        slack_installation.user_scopes = installation.user_scopes
        slack_installation.incoming_webhook_url = (
            installation.incoming_webhook_url
        )
        slack_installation.incoming_webhook_channel = (
            installation.incoming_webhook_channel
        )
        slack_installation.incoming_webhook_channel_id = (
            installation.incoming_webhook_channel_id
        )
        slack_installation.incoming_webhook_configuration_url = (
            installation.incoming_webhook_configuration_url
        )
        slack_installation.is_enterprise_install = (
            installation.is_enterprise_install
        )
        slack_installation.token_type = installation.token_type
        slack_installation.installed_at = installed_at

        slack_installation.save()
        self.save_bot(installation.to_bot())

    def save_bot(self, bot: Bot):
        installed_at = bot.installed_at
        bot_token_expires_at = bot.bot_token_expires_at

        if installed_at is not None:
            installed_at = datetime.datetime.fromtimestamp(installed_at)
            if is_naive(installed_at):
                installed_at = make_aware(installed_at)

        if bot_token_expires_at is not None:
            bot_token_expires_at = datetime.datetime.fromtimestamp(
                bot_token_expires_at
            )
            if is_naive(bot_token_expires_at):
                bot_token_expires_at = make_aware(bot_token_expires_at)

        slack_bot = SlackBot.objects.filter(
            client_id=self.client_id,
            enterprise_id=bot.enterprise_id,
            team_id=bot.team_id,
            installed_at=installed_at,
        ).first()

        if slack_bot is None:
            slack_bot = SlackBot()

        slack_bot.client_id = self.client_id
        slack_bot.app_id = bot.app_id
        slack_bot.enterprise_id = bot.enterprise_id
        slack_bot.enterprise_name = bot.enterprise_name
        slack_bot.team_id = bot.team_id
        slack_bot.team_name = bot.team_name
        slack_bot.bot_token = bot.bot_token
        slack_bot.bot_refresh_token = bot.bot_refresh_token
        slack_bot.bot_token_expires_at = bot_token_expires_at
        slack_bot.bot_id = bot.bot_id
        slack_bot.bot_user_id = bot.bot_user_id
        slack_bot.bot_scopes = bot.bot_scopes
        slack_bot.is_enterprise_install = bot.is_enterprise_install
        slack_bot.installed_at = installed_at

        slack_bot.save()

    def find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Bot]:
        if is_enterprise_install:
            team_id = None
        row = (
            SlackBot.objects.filter(
                client_id=self.client_id,
                enterprise_id=enterprise_id,
                team_id=team_id,
            )
            .order_by(F("installed_at").desc())
            .first()
        )
        if row:
            return Bot(
                app_id=row.app_id,
                enterprise_id=row.enterprise_id,
                team_id=row.team_id,
                bot_token=row.bot_token,
                bot_refresh_token=row.bot_refresh_token,
                bot_token_expires_at=row.bot_token_expires_at,
                bot_id=row.bot_id,
                bot_user_id=row.bot_user_id,
                bot_scopes=row.bot_scopes,
                installed_at=row.installed_at,
            )
        return None

    # an installation is look up
    def find_installation(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        user_id: Optional[str] = None,
        is_enterprise_install: Optional[bool] = False,
    ) -> Optional[Installation]:
        if is_enterprise_install:
            team_id = None
        if user_id is None:
            row = (
                SlackInstallation.objects.filter(
                    client_id=self.client_id,
                    enterprise_id=enterprise_id,
                    team_id=team_id,
                )
                .order_by(F("installed_at").desc())
                .first()
            )
        else:
            row = (
                SlackInstallation.objects.filter(
                    client_id=self.client_id,
                    enterprise_id=enterprise_id,
                    team_id=team_id,
                    user_id=user_id,
                )
                .order_by(F("installed_at").desc())
                .first()
            )

        if not row:
            return None  # no installation found

        installation = Installation(
            app_id=row.app_id,
            enterprise_id=row.enterprise_id,
            team_id=row.team_id,
            bot_token=row.bot_token,
            bot_refresh_token=row.bot_refresh_token,
            bot_token_expires_at=row.bot_token_expires_at,
            bot_id=row.bot_id,
            bot_user_id=row.bot_user_id,
            bot_scopes=row.bot_scopes,
            user_id=row.user_id,
            user_token=row.user_token,
            user_refresh_token=row.user_refresh_token,
            user_token_expires_at=row.user_token_expires_at,
            user_scopes=row.user_scopes,
            incoming_webhook_url=row.incoming_webhook_url,
            incoming_webhook_channel_id=row.incoming_webhook_channel_id,
            incoming_webhook_configuration_url=row.incoming_webhook_configuration_url,
            installed_at=row.installed_at,
        )

        if user_id is not None:
            # Fetch the latest bot token
            latest_bot_row = (
                SlackInstallation.objects.filter(
                    client_id=self.client_id,
                    enterprise_id=enterprise_id,
                    team_id=team_id,
                )
                .exclude(bot_token__isnull=True)
                .order_by(F("installed_at").desc())
                .first()
            )

            if latest_bot_row:
                installation.bot_id = latest_bot_row.bot_id
                installation.bot_user_id = latest_bot_row.bot_user_id
                installation.bot_scopes = latest_bot_row.bot_scopes
                installation.bot_token = latest_bot_row.bot_token
                installation.bot_refresh_token = (
                    latest_bot_row.bot_refresh_token
                )
                installation.bot_token_expires_at = (
                    latest_bot_row.bot_token_expires_at
                )

        return installation


class DjangoOAuthStateStore(OAuthStateStore):
    expiration_seconds: int

    def __init__(
        self,
        expiration_seconds: int,
        logger: Logger,
    ):
        self.expiration_seconds = expiration_seconds
        self._logger = logger

    # Generate a random state value and store it in the database
    def issue(self) -> str:
        state: str = str(uuid4())
        expire_at = timezone.now() + timezone.timedelta(
            seconds=self.expiration_seconds
        )
        row = SlackOAuthState(state=state, expire_at=expire_at)
        row.save()
        return state

    # Consume a state value and return True if it exists in the database and is not expired
    def consume(self, state: str) -> bool:
        rows = SlackOAuthState.objects.filter(state=state).filter(
            expire_at__gte=timezone.now()
        )
        if rows.count() > 0:
            rows.delete()
            return True
        return False
