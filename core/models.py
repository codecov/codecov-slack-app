from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone


class DateTimeWithoutTZField(models.DateTimeField):
    def db_type(self, connection):
        return "timestamp"


class NotificationFilters(models.TextChoices):
    AUTHOR = "author"
    BRANCH = "branch"
    REVIEWER = "reviewer"


# Create your models here.
class SlackBot(models.Model):
    client_id = models.CharField(null=False, max_length=32)
    app_id = models.CharField(null=False, max_length=32)
    enterprise_id = models.CharField(null=True, max_length=32)
    enterprise_name = models.TextField(null=True)
    team_id = models.CharField(null=True, max_length=32)
    team_name = models.TextField(null=True)
    bot_token = models.TextField(null=True)
    bot_refresh_token = models.TextField(null=True)
    bot_token_expires_at = models.DateTimeField(null=True)
    bot_id = models.CharField(null=True, max_length=32)
    bot_user_id = models.CharField(null=True, max_length=32)
    bot_scopes = models.TextField(null=True)
    is_enterprise_install = models.BooleanField(null=True)
    installed_at = models.DateTimeField(null=False)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "client_id",
                    "enterprise_id",
                    "team_id",
                    "installed_at",
                ]
            ),
        ]


class SlackInstallation(models.Model):
    client_id = models.CharField(null=False, max_length=32)
    app_id = models.CharField(null=False, max_length=32)
    enterprise_id = models.CharField(null=True, max_length=32)
    enterprise_name = models.TextField(null=True)
    enterprise_url = models.TextField(null=True)
    team_id = models.CharField(null=True, max_length=32)
    team_name = models.TextField(null=True)
    bot_token = models.TextField(null=True, unique=True)
    bot_refresh_token = models.TextField(null=True)
    bot_token_expires_at = models.DateTimeField(null=True)
    bot_id = models.CharField(null=True, max_length=32)
    bot_user_id = models.TextField(null=True)
    bot_scopes = models.TextField(null=True)
    user_id = models.CharField(null=False, max_length=32)
    user_token = models.TextField(null=True)
    user_refresh_token = models.TextField(null=True)
    user_token_expires_at = models.DateTimeField(null=True)
    user_scopes = models.TextField(null=True)
    incoming_webhook_url = models.TextField(null=True)
    incoming_webhook_channel = models.TextField(null=True)
    incoming_webhook_channel_id = models.TextField(null=True)
    incoming_webhook_configuration_url = models.TextField(null=True)
    is_enterprise_install = models.BooleanField(null=True)
    token_type = models.CharField(null=True, max_length=32)
    installed_at = models.DateTimeField(null=False)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "client_id",
                    "enterprise_id",
                    "team_id",
                    "user_id",
                    "installed_at",
                ]
            ),
        ]


class SlackOAuthState(models.Model):
    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "state",
                ]
            ),
        ]

    state = models.CharField(null=False, max_length=64)
    expire_at = models.DateTimeField(null=False)


CHANNEL_ID_LENGTH = 21


class Notification(models.Model):
    installation = models.ForeignKey(
        SlackInstallation,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    repo = models.TextField(null=True)
    owner = models.TextField(null=True)
    channels = ArrayField(
        models.CharField(
            max_length=CHANNEL_ID_LENGTH,
        ),
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("installation", "repo", "owner"),)
        indexes = [
            models.Index(
                fields=[
                    "installation",
                    "repo",
                    "owner",
                ]
            )
        ]


class StatusOptions(models.TextChoices):
    SUCCESS = "success"
    ERROR = "error"


class NotificationStatus(models.Model):
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="statuses",
    )
    status = models.CharField(
        max_length=7,
        choices=StatusOptions.choices,
    )
    pullid = models.TextField(null=True)
    created_at = DateTimeWithoutTZField(auto_now_add=True)
    updated_at = DateTimeWithoutTZField(auto_now=True)
    message_timestamp = models.TextField(
        null=True
    )  # message timestamp https://api.slack.com/methods/chat.update#arg_ts
    channel = models.TextField(null=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["notification", "status", "pullid", "channel"]
            )
        ]


class NotificationConfig(models.Model):
    installation = models.ForeignKey(
        SlackInstallation,
        on_delete=models.CASCADE,
        related_name="notification_config",
    )
    repo = models.TextField(null=True)
    owner = models.TextField(null=True)
    channel = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filters = ArrayField(
        models.JSONField(null=True),
        blank=True,
        null=True,
    )

    class Meta:
        unique_together = (("installation", "repo", "owner", "channel"),)
        indexes = [
            models.Index(fields=["installation", "repo", "owner", "channel"])
        ]


class NotificationConfigStatus(models.Model):
    notification_config = models.ForeignKey(
        NotificationConfig,
        on_delete=models.CASCADE,
        related_name="notification_config_statuses",
    )
    status = models.CharField(
        max_length=7,
        choices=StatusOptions.choices,
        default=StatusOptions.SUCCESS,
    )
    pullid = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    message_timestamp = models.TextField(
        null=True
    )  # unique identifier for the message in slack https://api.slack.com/methods/chat.update#arg_ts

    class Meta:
        indexes = [
            models.Index(fields=["notification_config", "status", "pullid"])
        ]
