# Generated by Django 4.1.9 on 2023-05-16 10:56

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_slackoauthstate_core_slacko_state_dbac4e_idx"),
    ]

    operations = [
        migrations.AlterField(
            model_name="slackinstallation",
            name="bot_token",
            field=models.TextField(null=True, unique=True),
        ),
        migrations.CreateModel(
            name="Notification",
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
                ("repo", models.TextField(null=True)),
                ("owner", models.TextField(null=True)),
                (
                    "channels",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=21),
                        blank=True,
                        null=True,
                        size=None,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "installation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to="core.slackinstallation",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["installation", "repo", "owner"],
                name="core_notifi_install_7fc51b_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="notification",
            unique_together={("installation", "repo", "owner")},
        ),
    ]
