# Generated by Django 4.1.7 on 2023-04-25 16:12

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("service_auth", "0002_alter_service_service_userid"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="service",
            unique_together={("user", "name", "service_userid")},
        ),
    ]
