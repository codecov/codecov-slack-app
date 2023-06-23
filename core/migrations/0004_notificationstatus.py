# Generated by Django 4.2.1 on 2023-06-14 17:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "core",
            "0003_alter_slackinstallation_bot_token_notification_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationStatus",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("error", "Error")],
                        default="success",
                        max_length=7,
                    ),
                ),
                ("pullid", models.TextField(null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("message_ts", models.TextField(null=True)),
                ("channel", models.TextField(null=True)),
                (
                    "notification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="statuses",
                        to="core.notification",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["notification", "status", "pullid", "channel"],
                        name="core_notifi_notific_7aa2e0_idx",
                    )
                ],
            },
        ),
    ]