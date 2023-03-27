from django.db import models


# Create your models here.
class ServiceOptions(models.TextChoices):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class SlackUser(models.Model):
    user_id = models.CharField(max_length=50, unique=True)
    username = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=100, null=True)
    display_name = models.CharField(max_length=100, null=True)
    team_id = models.CharField(max_length=50, null=True)
    is_bot = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_owner = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    codecov_access_token = models.UUIDField(unique=True, null=True, blank=True)

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
        SlackUser, on_delete=models.CASCADE, related_name="services"
    )
    service_name = models.CharField(
        max_length=50, choices=ServiceOptions.choices
    )
    service_id = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.service_name

    class Meta:
        indexes = [
            models.Index(fields=["service_name", "service_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.active:
            # Deactivate all other services for this user
            Service.objects.filter(user=self.user, active=True).update(
                active=False
            )
        super().save(*args, **kwargs)
