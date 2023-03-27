# Generated by Django 4.1.7 on 2023-03-27 13:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Service",
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
                    "service_name",
                    models.CharField(
                        choices=[
                            ("github", "Github"),
                            ("gitlab", "Gitlab"),
                            ("bitbucket", "Bitbucket"),
                        ],
                        max_length=50,
                    ),
                ),
                ("service_id", models.CharField(max_length=50, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("active", models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name="SlackUser",
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
                ("user_id", models.CharField(max_length=50, unique=True)),
                ("username", models.CharField(max_length=100, null=True)),
                ("email", models.CharField(max_length=100, null=True)),
                ("display_name", models.CharField(max_length=100, null=True)),
                ("team_id", models.CharField(max_length=50, null=True)),
                ("is_bot", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_owner", models.BooleanField(default=False)),
                ("is_admin", models.BooleanField(default=False)),
                (
                    "codecov_access_token",
                    models.UUIDField(blank=True, null=True, unique=True),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="slackuser",
            index=models.Index(
                fields=["user_id"], name="service_aut_user_id_2e94eb_idx"
            ),
        ),
        migrations.AddField(
            model_name="service",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="services",
                to="service_auth.slackuser",
            ),
        ),
        migrations.AddIndex(
            model_name="service",
            index=models.Index(
                fields=["service_name", "service_id"],
                name="service_aut_service_c6cb47_idx",
            ),
        ),
    ]
