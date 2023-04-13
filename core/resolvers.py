import logging

from service_auth.actions import get_or_create_slack_user, view_login_modal, authenticate_command
from service_auth.models import Service, SlackUser

logger = logging.getLogger(__name__)


def service_logout(client, command, say):
    """Logout of current active service"""
    slack_user_id = command["user_id"]
    user_info = client.users_info(user=slack_user_id)

    user = get_or_create_slack_user(user_info)
    if user.active_service is None:
        say("You are not logged in to any service")
        return

    service = Service.objects.get(user=user, name=user.active_service)
    service.active = False
    service.save()

    user.codecov_access_token = None
    user.save()

    say(f"Successfully logged out of {service.name}")


def service_login(client, command, say):
    """Login to a service -- overrides current active service"""
    try:
        view_login_modal(client, command)

    except Exception as e:
        logger.error(e)
        say(
            "There was an error processing your request. Please try again later."
        )

