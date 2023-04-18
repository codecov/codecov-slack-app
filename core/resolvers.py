import logging

from core.helpers import validate_owner_params
from service_auth.actions import (authenticate_command,
                                  get_or_create_slack_user,
                                  handle_codecov_public_api_request,
                                  view_login_modal)
from service_auth.models import Service

logger = logging.getLogger(__name__)


def resolve_service_logout(client, command, say):
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


def resolve_service_login(client, command, say):
    """Login to a service -- overrides current active service"""

    view_login_modal(client, command)


def resolve_organizations(client, command, say):
    """Get a list of organizations that the user is a member of"""
    try:
        authenticate_command(client, command)
        codecov_response = handle_codecov_public_api_request(
            user_id=command["user_id"], endpoint_name="service_owners"
        )
        results = codecov_response["results"]

        formatted_response = "*Organizations you have access to are:*\n\n"
        for result in results:  # maybe take this out to a helper function
            for key, value in result.items():
                formatted_response += f"*{key.capitalize()}*: {value}\n"
            formatted_response += "\n"

        say(formatted_response)

    except Exception as e:
        logger.error(e)
        say(
            "There was an error processing your request. Please try again later."
        )


def resolve_owner(client, command, say):
    """Get owner's information"""
    command_text = command["text"].split(" ")
    if len(command_text) < 3:
        say("Please provide a username and service")
        return
    owner_username = command_text[1].split("=")[1]
    service = command_text[2].split("=")[1]
    user_id = command["user_id"]

    try:
        normalized_name = validate_owner_params(owner_username, service, say)
        data = handle_codecov_public_api_request(
            user_id=user_id,
            endpoint_name="owner",
            owner_username=owner_username,
            service=normalized_name,
        )

        formatted_data = f"*Owner information for {owner_username}*:\n\n Service: {data['service']}\nUsername: {data['username']}\nName: {data['name']}"
        say(formatted_data)

    except Exception as e:
        logger.error(e)
        say(
            f"{e if e else 'There was an error processing your request. Please try again later.'}"
        )


def resolve_help(say):
    """Get help"""
    message_payload = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Hi There 👋!  here are some of the things you can do:",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Commands:* \n\n`/codecov login` - Login to a service\n `/codecov logout` - Logout of current active service\n`/codecov organizations` - Get a list of organizations that user has access to\n`/codecov owner username=<username> service=<service>` - Get owner's information",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Note* that the order of the variables in your command text is important for the command to be processed correctly.",
            },
        },
    ]

    say(
        text="",
        blocks=message_payload,
    )
