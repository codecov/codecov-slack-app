import logging

from core.helpers import (extract_command_params, extract_optional_params,
                          validate_service)
from service_auth.actions import (authenticate_command,
                                  get_or_create_slack_user,
                                  handle_codecov_public_api_request,
                                  view_login_modal)
from service_auth.models import Service

from .enums import EndpointName

logger = logging.getLogger(__name__)


class BaseResolver:
    def __init__(self, client, command, say):
        self.client = client
        self.command = command
        self.say = say

    def __call__(self):
        try:
            params_dict = extract_command_params(command=self.command)
            optional_params = extract_optional_params(
                params_dict, command=self.command
            )

            service = params_dict.get("service")
            if service:
                normalized_service = validate_service(service)
                params_dict["service"] = normalized_service

            res = self.resolve(params_dict, optional_params)
            self.say(res)

        except Exception as e:
            logger.error(e)
            self.say(
                f"{e if e else 'There was an error processing your request. Please try again later.'}"
            )

    def resolve(self, *args, **kwargs):
        raise NotImplementedError("must implement resolve in subclass")


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


class OrgsResolver(BaseResolver):
    """Get a list of organizations that the user is a member of"""

    def resolve(self, params_dict, optional_params):
        authenticate_command(client=self.client, command=self.command)
        codecov_response = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.SERVICE_OWNERS,
        )
        results = codecov_response["results"]

        formatted_response = "*Organizations you have access to are:*\n\n"
        for result in results:  # maybe take this out to a helper function
            for key, value in result.items():
                formatted_response += f"*{key.capitalize()}*: {value}\n"
            formatted_response += "\n"

        return formatted_response


class OwnerResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Get owner's information"""
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.OWNER,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        owner_username = params_dict.get("username")
        formatted_data = f"*Owner information for {owner_username}*:\n\n Service: {data['service']}\nUsername: {data['username']}\nName: {data['name']}"
        return formatted_data


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
                "text": "*Auth commands:*\n`/codecov login` - Login to a service\n `/codecov logout` - Logout of current active service\n\n\n*Users commands:*\n`/codecov organizations` - Get a list of organizations that user has access to\n`/codecov owner username=<username> service=<service>` - Get owner's information\n`/codecov users username=<username> service=<service>` Optional params: `is_admin=<is_admin> activated=<activated> page=<page> per_page=<per_page>` - Get a list of users for the specified owner\n\n\n*Repositories commands:*\n`/codecov repos username=<username> service=<service>` Optional params: `names=<names> active=<active> page=<page> per_page=<per_page>` - Get a list of repos for the specified owner\n`/codecov repo repository=<repository> username=<username> service=<service>` - Get repo information\n`/codecov repo-config username=<username> service=<service> repository=<repository>` - Get the repository configuration for the specified owner and repository \n `/codecov help` - Get help \n\n",
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


class UsersResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Returns a paginated list of users for the specified owner"""
        authenticate_command(client=self.client, command=self.command)
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.USERS_LIST,
            service=params_dict.get("service"),
            optional_params=optional_params,
            params_dict=params_dict,
        )

        owner_username = params_dict.get("username")
        if data["count"] == 0:
            return f"No users found for {owner_username}"

        formatted_data = f"*Users for {owner_username}*\n\n"
        for user in data["results"]:
            formatted_data += f"Username: {user['username']}\nName: {user['name']}\nEmail: {user['email']}\nActivated: {user['activated']}\nAdmin: {user['is_admin']}\n\n"
        return formatted_data


class RepoConfigResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Returns the repository configuration for the specified owner and repository"""
        authenticate_command(client=self.client, command=self.command)

        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.REPO_CONFIG,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        owner_username = params_dict.get("username")
        formatted_data = f"*Repository configuration for {owner_username}*\n\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        return formatted_data


class RepoResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Returns a single repository by name for the specified owner"""
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.REPO,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repository = params_dict.get("repository")

        formatted_data = f"*Repository {repository}*\n\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        return formatted_data


class ReposResolver(BaseResolver):
    """Returns a paginated list of repositories for the specified owner"""

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.REPOS,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        owner_username = params_dict.get("username")

        if data["count"] == 0:
            return f"No repositories found for {owner_username}"

        formatted_data = f"*Repositories for {owner_username}*\n\n"
        for repo in data["results"]:
            formatted_data += f"**Name: {repo['name']}**\nUpdate stamp: {repo['updatestamp']}\nBranch: {repo['branch']}\nPrivate: {repo['private']}\nLanguage: {repo['language']}\nActive: {repo['active']}\nActivated: {repo['activated']} \n\nAuthor username: {repo['author']['username']}\nAuthor service: {repo['author']['service']}\n------------------\n"
        return formatted_data


class BranchesResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Returns a paginated list of branches for the specified owner and repository"""
        authenticate_command(client=self.client, command=self.command)
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.BRANCHES,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No branches found for {repo}"

        formatted_data = f"*Branches for {repo}*\n\n"
        for branch in data["results"]:
            formatted_data += f"**Name: {branch['name']}**\nUpdate stamp: {branch['updatestamp']}\n------------------\n"
        return formatted_data


class BranchResolver(BaseResolver):
    def resolve(self, params_dict, optional_params):
        """Returns a single branch by name for the specified owner and repository"""
        authenticate_command(client=self.client, command=self.command)
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=EndpointName.BRANCH,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repo = params_dict.get("repository")
        branch = params_dict.get("branch")

        if data:
            formatted_data = f"*Branch {branch} for {repo}*\n\n"
            for key in data:
                formatted_data += (
                    f"{key.capitalize()}: {data[key]}\n"  # the response is big
                )

        return f"Branch {branch} found for {repo} \n\n{formatted_data}"
