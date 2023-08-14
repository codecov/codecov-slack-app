import json
import logging

from slack_sdk.errors import SlackApiError

from core.helpers import (configure_notification, endpoint_mapping,
                          extract_command_params, extract_optional_params,
                          format_nested_keys, validate_comparison_params,
                          validate_service)
from core.models import Notification, SlackInstallation, NotificationConfig, NotificationStatus, NotificationConfigStatus
from service_auth.actions import (authenticate_command,
                                  get_or_create_slack_user,
                                  handle_codecov_public_api_request,
                                  view_login_modal)
from service_auth.models import Service

from .enums import EndpointName

logger = logging.getLogger(__name__)

SIZE_THRESHOLD = 4000


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

            if res:
                if len(res) > SIZE_THRESHOLD:
                    self.post_snippet(res)
                else:
                    self.client.chat_postEphemeral(
                        channel=self.command["channel_id"],
                        user=self.command["user_id"],
                        text=res,
                    )

        except Exception as e:
            logger.error(e)

            self.client.chat_postEphemeral(
                channel=self.command["channel_id"],
                user=self.command["user_id"],
                text=f"{e if e else 'There was an error processing your request. Please try again later.'}",
            )

    def resolve(self, *args, **kwargs):
        raise NotImplementedError("must implement resolve in subclass")

    def post_snippet(self, message):
        try:
            response = self.client.conversations_info(channel=self.command["channel_id"])
            channel = response['channel']

            # Check if it's not a DM with App
            if not channel['is_im']:
                self.client.chat_postEphemeral(
                channel=self.command["channel_id"],
                user=self.command["user_id"],
                text=f"Response too large to display here. you can find it in the Codecov app's DMs",
            )

            # Upload the file to bot's direct message
            response = self.client.files_upload(
                channels=self.command["user_id"],
                content=message,
                filetype="javascript",
                filename="codecov.json",
                title="Codecov JSON",
            )

            if response["ok"]:
                file_id = response["file"]["id"]
                print(f"File {file_id} uploaded successfully!")
            else:
                print(
                    f"Failed to upload the file. Error: {response['error']} {file_id}"
                )

        except SlackApiError as e:
            print(f"Error posting message: {e}")


def resolve_service_logout(client, command, say):
    """Logout of current active service"""
    slack_user_id = command["user_id"]
    user_info = client.users_info(user=slack_user_id)

    user = get_or_create_slack_user(user_info)
    if user.active_service is None:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=slack_user_id,
            text="You are not logged in to any service",
        )
        return

    service = Service.objects.get(user=user, name=user.active_service)
    service.active = False
    service.save()

    user.codecov_access_token = None
    user.save()

    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=slack_user_id,
        text=f"Successfully logged out of {service.name}",
    )


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


def resolve_help(channel_id, user_id, client):
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
                "text": "`/codecov organizations` - Get a list of organizations that user has access to\n\n`/codecov commits username=<org_name> service=<service> repository=<repository>` Optional params: `branch=<branch> page=<page> page_size=<page_size>` - Get a list of commits for the repository\n\n`/codecov pulls username=<org_name> service=<service> repository=<repository>` Optional params: `ordering=<ordering> page=<page> page_size=<page_size> state=<closed,open,merged>` - Get a list of pulls for the repository\n\n`/codecov repos username=<org_name> service=<service>` Optional params: `names=<names> active=<active> page=<page> page_size=<page_size>` - Get a list of repos for the specified owner\n\n`/codecov compare username=<org_name> service=<service> repository=<repository>` - Get a comparison between two commits or a pull and its base\n\n _*NOTE*_\n _You must either pass `pullid=<pullid>` or both of `head=<head> base=<base>` in the comparison commands_\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Notifications commands 📳*:\n`/codecov notify username=<org_name> service=<service> repository=<repository>` - Direct Notifications for a specific repo to a specific channel\n`/codecov notify-off username=<org_name> service=<service> repository=<repository>` - Turn off Notifications for a specific repo in a specific channel\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "`/codecov help` - Get help\n*Note* that some of commands require you to login to a service first. \n\n",
            },
        },
    ]

    client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
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


class ComparisonResolver(BaseResolver):
    """Gets a comparison for all types of comparisons"""

    def __init__(self, command, client, say, command_name):
        super().__init__(command, client, say)
        self.command_name = command_name

    def resolve(self, params_dict, optional_params):
        validate_comparison_params(optional_params)
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        base = params_dict.get("base")
        head = params_dict.get("head")
        pullid = params_dict.get("pullid")
        repo = params_dict.get("repository")

        if pullid:
            head = data["head_commit"]
            base = data["base_commit"]

        if data:
            title = f"*Comparison of `{base}` and `{head}` for {repo}*\n\n"
            return title + json.dumps(data, indent=4, sort_keys=True)

        return f"Comparison of {base} and {head} for {repo} not found"


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


class CoverageTrendsResolver(BaseResolver):
    """Returns a paginated list of coverage trends for the specified owner and repository"""

    command_name = EndpointName.COVERAGE_TRENDS

    def resolve(self, params_dict, optional_params):
        optional_params["interval"] = "1d"  # set a default interval of 1 day
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            service=params_dict.get("service"),
            params_dict=params_dict,
            optional_params=optional_params,
        )

        flag = params_dict.get("flag")
        if data["count"] == 0:
            return f"No coverage trends found for {flag}"

        formatted_data = f"*Coverage trends for {flag}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)


class CoverageTrendResolver(BaseResolver):
    """Returns a paginated list of timeseries measurements aggregated by the specified interval"""

    command_name = EndpointName.COVERAGE_TREND

    def resolve(self, params_dict, optional_params):
        optional_params["interval"] = "1d"
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        if data["count"] == 0:
            return f"No coverage trend found for {repo}"

        formatted_data = f"*Coverage trend for {repo}*: ({data['count']})\n"
        return format_nested_keys(data, formatted_data)


class FileCoverageReport(BaseResolver):
    """Returns coverage info for a single file specified by path."""

    command_name = EndpointName.FILE_COVERAGE_REPORT

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        path = params_dict.get("path")
        if not data:
            return f"No coverage report found for {path} in {repo}"

        formatted_data = (
            f"*Coverage report for {path} in {repo}*:\n"
        )
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"

        return formatted_data


class CommitCoverageReport(BaseResolver):
    """returns line-by-line coverage info (hit=0/miss=1/partial=2)."""

    command_name = EndpointName.COMMIT_COVERAGE_REPORT

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        sha = params_dict.get("sha")

        commit = "head of the default branch" if not sha else sha
        if not data:
            return f"No coverage report found for {commit} in {repo}"

        formatted_data = f"*Coverage report for {commit} in {repo}*:\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        return formatted_data


class CommitCoverageTotals(BaseResolver):
    """Returns the coverage totals for a given commit and the coverage totals broken down by file."""

    command_name = EndpointName.COMMIT_COVERAGE_TOTALS

    def resolve(self, params_dict, optional_params):
        data = handle_codecov_public_api_request(
            user_id=self.command["user_id"],
            endpoint_name=self.command_name,
            params_dict=params_dict,
            optional_params=optional_params,
        )

        repo = params_dict.get("repository")
        sha = params_dict.get("sha")

        commit = "head of the default branch" if not sha else sha
        if not data:
            return f"No coverage report found for {commit} in {repo}"

        formatted_data = f"*Coverage report for {commit} in {repo}*\n"
        for key in data:
            formatted_data += f"{key.capitalize()}: {data[key]}\n"
        return formatted_data


class NotificationResolver(BaseResolver):
    """Saves a user's notification preferences for a repository"""

    def __init__(self, command, client, say, notify=False):
        super().__init__(client, command, say)
        self.notify = notify

    command_name = EndpointName.NOTIFICATION

    def resolve(self, params_dict, optional_params):
        bot_token = self.client.token
        user_id = self.command["user_id"]
        channel_id = self.command["channel_id"]
        installation = SlackInstallation.objects.get(
            bot_token=bot_token,
        )

        notification = Notification.objects.filter(
            repo=params_dict["repository"],
            owner=params_dict["username"],
            installation=installation,
        ).first()

        # Disable notifications
        if not self.notify:
            if not notification:
                return f"Notification is not enabled for {params_dict['repository']} in this channel 👀"

            if not (channel_id in notification.channels):
                return f"Notification is not enabled for {params_dict['repository']} in this channel 👀"

            notification.channels.remove(channel_id)
            notification.save()

            if not notification.channels:
                # No channels left, delete notification
                notification.delete()

            return f"Notifications disabled for {params_dict['repository']} in this channel 📴"

        # Notification already exists
        if notification:
            if notification.channels and channel_id in notification.channels:
                return f"Notification already enabled for {params_dict['repository']} in this channel 👀"

        user_info = self.client.users_info(user=user_id)
        user = get_or_create_slack_user(user_info)

        # Is repo public or private
        data = handle_codecov_public_api_request(
            user_id=user_id,
            endpoint_name=EndpointName.REPO,
            service=params_dict.get("service"),
            params_dict=params_dict,
        )

        if not data:
            msg = (
                f" Please use `/codecov login` if you are requesting notifications for a private repo."
                if not user.codecov_access_token
                else ""
            )

            raise Exception(f"Error: 404 Repo Not Found.{msg}")

        params_dict["slack__bot_token"] = bot_token
        params_dict["slack__channel_id"] = channel_id

        # Configure notifications if repo is public
        if data["private"] == False:
            return configure_notification(data=params_dict)

        else:
            repo_name = params_dict["repository"]
            # Double check if user approve of notifications for private repo
            self.client.views_open(
                trigger_id=self.command["trigger_id"],
                view={
                    "type": "modal",
                    "private_metadata": json.dumps(params_dict),
                    "title": {
                        "type": "plain_text",
                        "text": "Codecov Notifications",
                    },
                    "blocks": [
                        {"type": "divider"},
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Are you sure you want to turn notifications on for {repo_name}?",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "_Note: This is a private repo_",
                                }
                            ],
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Yes",
                                    },
                                    "style": "primary",
                                    "value": "approve",
                                    "action_id": "approve-notification",
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Nope",
                                    },
                                    "style": "danger",
                                    "value": "decline",
                                    "action_id": "decline-notification",
                                },
                            ],
                        },
                        {"type": "divider"},
                    ],
                },
            )


def resolve_migrate(client, command, say):
    """Migrates all notifications from the old to the new format."""

    notifications = Notification.objects.all()
    for notification in notifications:
        for channel in notification.channels:
            new_notification = NotificationConfig(
                installation=notification.installation,
                repo=notification.repo,
                owner=notification.owner,
                channel=channel,
                created_at=notification.created_at,
                updated_at=notification.updated_at,
            )

            new_notification.save()

            notification_channel_statuses = NotificationStatus.objects.filter(
                notification=notification,
                channel=channel,
            )

            if not notification_channel_statuses:
                continue

            for notification_status in notification_channel_statuses:
                new_status = NotificationConfigStatus(
                    notification_config=new_notification,
                    pullid=notification_status.pullid,
                )
                new_status.save()

            
    say(f"Successfully migrated all channels")





