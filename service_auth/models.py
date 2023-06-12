from django.db import models
from core.models import SlackInstallation

# Create your models here.
class ServiceOptions(models.TextChoices):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class SlackUser(models.Model):
    user_id = models.CharField(primary_key=True, max_length=50)
    username = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=100, null=True)
    display_name = models.CharField(max_length=100, null=True)
    installation = models.ForeignKey(
        SlackInstallation,
        on_delete=models.CASCADE,
        related_name="slackuser",
        default=1,
    )
    is_bot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_owner = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    codecov_access_token = models.UUIDField(null=True, blank=True)

    def __str__(self):
        return self.display_name or self.username or self.user_id

    class Meta:
        indexes = [
            models.Index(fields=["user_id"]),
        ]

    @property
    def active_service(self):
        try:
            return self.services.get(active=True)
        except Service.DoesNotExist:
            return None


class Service(models.Model):
    user = models.ForeignKey(
        SlackUser,
        on_delete=models.CASCADE,
        related_name="services",
        db_column="user_id",
        max_length=50,
    )
    name = models.CharField(max_length=50, choices=ServiceOptions.choices)
    service_userid = models.CharField(max_length=50)
    service_username = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["name", "user"]),
        ]
        unique_together = ("user", "name", "service_userid")

    def save(self, *args, **kwargs):
        if self.active:
            # Deactivate all other services for this user
            Service.objects.filter(user=self.user, active=True).update(
                active=False
            )
        super().save(*args, **kwargs)
