import logging

from core.helpers import (extract_command_params, extract_optional_params,
                          format_nested_keys, validate_service)
from service_auth.actions import (authenticate_command,
                                  get_or_create_slack_user,
                                  handle_codecov_public_api_request,
                                  view_login_modal)
from service_auth.models import Service

from .enums import EndpointName
from .helpers import endpoint_mapping

logger = logging.getLogger(__name__)


class BaseResolver:
    command_name = None

    def __init__(self, client, command, say):
        self.client = client
        self.command = command
        self.say = say

    def __call__(self):
        try:
            command = endpoint_mapping.get(self.command_name)
            if command.is_private:
                authenticate_command(
                    client=self.client,
                    command=self.command,
                )

            params_dict = extract_command_params(
                command=self.command, command_name=self.command_name
            )
            optional_params = extract_optional_params(
                params_dict, command_name=self.command_name
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

    command_name = EndpointName.SERVICE_OWNERS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
        )

        if data["count"] == 0:
            return "You are not a member of any organization"

        formatted_response = (
            f"*Organizations you have access to*: ({data['count']})\n\n"
        )
        return format_nested_keys(data, formatted_response)


class OwnerResolver(BaseResolver):
    """Get owner's information"""

    command_name = EndpointName.OWNER

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
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
                "text": "*Auth commands:*\n`/codecov login` - Login to a service\n`/codecov logout` - Logout of current active service\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Users commands:*\n`/codecov organizations` - Get a list of organizations that user has access to\n`/codecov owner username=<username> service=<service>` - Get owner's information\n`/codecov users username=<username> service=<service>` Optional params: `is_admin=<is_admin> activated=<activated> page=<page> page_size=<page_size>` - Get a list of users for the specified owner\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Repositories commands:*\n`/codecov repos username=<username> service=<service>` Optional params: `names=<names> active=<active> page=<page> page_size=<page_size>` - Get a list of repos for the specified owner\n`/codecov repo repository=<repository> username=<username> service=<service>` - Get repo information\n`/codecov repo-config username=<username> service=<service> repository=<repository>` - Get the repository configuration for the specified owner and repository\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Branches commands:*\n`/codecov branches username=<username> service=<service> repository=<repository>` Optional params: `ordering=<ordering> author=<author> page=<page> page_size=<page_size>` - Get a list of branches for the repository\n`/codecov branch repository=<repository> username=<username> service=<service> branch=<branch>` - Get branch information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Commits commands:*\n`/codecov commits username=<username> service=<service> repository=<repository>` Optional params: `branch=<branch> page=<page> page_size=<page_size>` - Get a list of commits for the repository\n`/codecov commit repository=<repository> username=<username> service=<service> commitid=<commitid>` - Get commit information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Pulls commands:*\n`/codecov pulls username=<username> service=<service> repository=<repository>` Optional params: `ordering=<ordering> page=<page> page_size=<page_size> state=<closed,open,merged>` - Get a list of pulls for the repository\n`/codecov pull repository=<repository> username=<username> service=<service> pullid=<pullid>` - Get pull information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "`/codecov help` - Get help\n*Note* that some of commands requires you to login to a service first. \n\n",
            },
        },
    ]

    say(
        text="",
        blocks=message_payload,
    )


class UsersResolver(BaseResolver):
    """Returns a paginated list of users for the specified owner"""

    command_name = EndpointName.USERS_LIST

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            optional_params=optional_params,
            params_dict=params_dict,
        )

        owner_username = params_dict.get("username")
        if data["count"] == 0:
            return f"No users found for {owner_username}"

        formatted_data = f"*Users for {owner_username}*: ({data['count']})\n\n"
        return format_nested_keys(data, formatted_data)


class RepoConfigResolver(BaseResolver):
    """Returns the repository configuration for the specified owner and repository"""

    command_name = EndpointName.REPO_CONFIG

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        owner_username = params_dict.get("username")
        formatted_data = f"*Repository configuration for {owner_username}*\n\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        return formatted_data


class RepoResolver(BaseResolver):
    """Returns a single repository by name for the specified owner"""

    command_name = EndpointName.REPO

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
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

    command_name = EndpointName.REPOS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        owner_username = params_dict.get("username")

        if data["count"] == 0:
            return f"No repositories found for {owner_username}"

        formatted_data = (
            f"*Repositories for {owner_username}*: ({data['count']})\n\n"
        )
        return format_nested_keys(data, formatted_data)


class BranchesResolver(BaseResolver):
    """Returns a paginated list of branches for the specified owner and repository"""

    command_name = EndpointName.BRANCHES

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No branches found for {repo}"

        formatted_data = f"*Branches for {repo}*: ({data['count']})\n\n"
        return format_nested_keys(data, formatted_data)


class BranchResolver(BaseResolver):
    """Returns a single branch by name for the specified owner and repository"""

    command_name = EndpointName.BRANCH

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
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


class CommitsResolver(BaseResolver):
    """Returns a paginated list of commits for the specified owner and repository"""

    command_name = EndpointName.COMMITS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No commits found for {repo}"

        formatted_data = f"*Commits for {repo}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)


class CommitResolver(BaseResolver):
    """Returns a single commit by commit ID for the specified owner and repository"""

    command_name = EndpointName.COMMIT

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repo = params_dict.get("repository")
        commit_id = params_dict.get("commitid")

        if data:
            formatted_data = f"*Commit {commit_id} for {repo}*\n\n"
            for key in data:
                formatted_data += f"{key.capitalize()}: {data[key]}\n"

        return formatted_data


class PullsResolver(BaseResolver):
    """Returns a paginated list of pull requests for the specified owner and repository"""

    command_name = EndpointName.PULLS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No pulls found for {repo}"

        formatted_data = f"*Pulls for {repo}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)


class PullResolver(BaseResolver):
    """Returns a single pull request by pull request ID for the specified owner and repository"""

    command_name = EndpointName.PULL

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        repo = params_dict.get("repository")
        pull_id = params_dict.get("pullid")

        if data:
            formatted_data = f"*Pull {pull_id} for {repo}*\n\n"
            for key in data:
                formatted_data += f"{key.capitalize()}: {data[key]}\n"

        return formatted_data


class ComponentsResolver(BaseResolver):
    """Returns a paginated list of components for the specified owner and repository"""

    command_name = EndpointName.COMPONENTS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if not len(data):
            return f"No components found for {repo}"

        formatted_data = f"*Components for {repo}*: ({len(data)})\n"
        for component in data:
            for key in component:
                formatted_data += f"{key.capitalize()}: {component[key]}\n"

            formatted_data += "---------------- \n"

        return formatted_data


class FlagsResolver(BaseResolver):
    """Returns a paginated list of flags for the specified owner and repository"""

    command_name = EndpointName.FLAGS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No flags found for {repo}"

        formatted_data = f"*Flags for {repo}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)


class CoverageTrendResolver(BaseResolver):
    """Returns a paginated list of coverage trends for the specified owner and repository"""

    command_name = EndpointName.COVERAGE_TREND

    def resolve(self, params_dict, optional_params):
        optional_params["interval"] = "1d"
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No coverage trends found for {repo}"

        formatted_data = f"*Coverage trends for {repo}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)
