import logging

from core.helpers import (extract_command_params,
                          extract_users_optional_params, validate_owner_params)
from service_auth.actions import (EndpointName, authenticate_command,
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
            user_id=command["user_id"],
            endpoint_name=EndpointName.SERVICE_OWNERS,
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
    user_id = command["user_id"]

    command_text = command["text"].split(" ")
    if len(command_text) < 3:
        say("Please provide a username and service")
        return

    params_dict = extract_command_params(command_text)

    owner_username = params_dict.get("username")
    service = params_dict.get("service")

    try:
        normalized_name = validate_owner_params(owner_username, service, say)
        data = handle_codecov_public_api_request(
            user_id=user_id,
            endpoint_name=EndpointName.OWNER,
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
                "text": "*Commands:* \n\n`/codecov login` - Login to a service\n `/codecov logout` - Logout of current active service\n`/codecov organizations` - Get a list of organizations that user has access to\n`/codecov owner username=<username> service=<service>` - Get owner's information\n`/codecov users username=<username> service=<service> [is_admin=<is_admin] [activated=<activated>] [page=<page>] [per_page=<per_page>]` - Get a list of users for the specified owner\n`/codecov repo-config username=<username> service=<service> repository=<repository>` - Get the repository configuration for the specified owner and repository \n `/codecov help` - Get help \n\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Note* that some of commands requires you to login to a service first. \n\n",
            },
        },
    ]

    say(
        text="",
        blocks=message_payload,
    )


def resolve_users(client, command, say):
    """Returns a paginated list of users for the specified owner"""
    user_id = command["user_id"]

    command_text = command["text"].split(" ")
    if len(command_text) < 3:
        say("Please provide a username and service")
        return

    params_dict = extract_command_params(command_text)

    owner_username = params_dict.get("username")
    service = params_dict.get("service")

    optional_params = extract_users_optional_params(params_dict)

    try:
        validate_owner_params(owner_username, service, say)
        authenticate_command(client, command)

        data = handle_codecov_public_api_request(
            user_id=user_id,
            endpoint_name=EndpointName.USERS_LIST,
            owner_username=owner_username,
            service=service,
            params=optional_params,
        )

        if data["count"] == 0:
            say(f"No users found for {owner_username}")
            return

        formatted_data = f"*Users for {owner_username}*\n\n"
        for user in data["results"]:
            formatted_data += f"Username: {user['username']}\nName: {user['name']}\nEmail: {user['email']}\nActivated: {user['activated']}\nAdmin: {user['is_admin']}\n\n"
        say(formatted_data)

    except Exception as e:
        logger.error(e)
        say(
            f"{e if e else 'There was an error processing your request. Please try again later.'}"
        )


def resolve_repo_config(client, command, say):
    """Returns the repository configuration for the specified owner and repository"""
    user_id = command["user_id"]

    command_text = command["text"].split(" ")
    if len(command_text) < 4:
        say("Please provide a username and service and repository name")
        return

    params_dict = extract_command_params(command_text)

    owner_username = params_dict.get("username")
    service = params_dict.get("service")
    repository = params_dict.get("repository")

    if not repository:
        say("Please provide a repository name")
        return

    try:
        validate_owner_params(owner_username, service, say)
        authenticate_command(client, command)

        data = handle_codecov_public_api_request(
            user_id=user_id,
            endpoint_name=EndpointName.REPO_CONFIG,
            service=service,
            owner_username=owner_username,
            repository=repository,
        )

        formatted_data = f"*Repository configuration for {owner_username}*\n\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        say(formatted_data)

    except Exception as e:
        logger.error(e)
        say(
            f"{e if e else 'There was an error processing your request. Please try again later.'}"
        )
