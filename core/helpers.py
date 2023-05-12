from dataclasses import dataclass
from typing import Dict, Optional

from slack_sdk.errors import SlackApiError
from core.models import Notification

from .enums import EndpointName


@dataclass
class Command:
    required_params: Optional[list] = None
    optional_params: Optional[list] = None
    is_private: bool = False

    def validate(self, params_dict):
        if bool(self.required_params):
            if len(params_dict) == 0:
                raise ValueError(
                    "Missing required parameters"
                )  # provide a help message

            for param in self.required_params:
                if param not in params_dict:
                    raise ValueError(f"Missing required parameter {param}")


endpoint_mapping: Dict[EndpointName, Command] = {
    EndpointName.SERVICE_OWNERS: Command(is_private=True),
    EndpointName.OWNER: Command(
        required_params=["username", "service"],
    ),
    EndpointName.USERS_LIST: Command(
        required_params=["username", "service"],
        optional_params=[
            "activated",
            "is_admin",
            "search",
            "page",
            "page_size",
        ],
        is_private=True,
    ),
    EndpointName.REPO_CONFIG: Command(
        required_params=["username", "service", "repository"],
        is_private=True,
    ),
    EndpointName.REPOS: Command(
        required_params=["username", "service"],
        optional_params=["active", "names", "search", "page", "page_size"],
    ),
    EndpointName.REPO: Command(
        required_params=["username", "service", "repository"],
    ),
    EndpointName.BRANCHES: Command(
        required_params=["username", "service", "repository"],
        optional_params=["author", "ordering", "page", "page_size"],
        is_private=True,
    ),
    EndpointName.BRANCH: Command(
        required_params=["username", "service", "repository", "branch"],
        is_private=True,
    ),
    EndpointName.COMMITS: Command(
        required_params=["username", "service", "repository"],
        optional_params=["branch", "page", "page_size"],
        is_private=True,
    ),
    EndpointName.COMMIT: Command(
        required_params=["username", "service", "repository", "commitid"],
        is_private=True,
    ),
    EndpointName.PULLS: Command(
        required_params=["username", "service", "repository"],
        optional_params=["ordering", "page", "page_size", "state"],
        is_private=True,
    ),
    EndpointName.PULL: Command(
        required_params=["username", "service", "repository", "pullid"],
        is_private=True,
    ),
    EndpointName.COMPONENTS: Command(
        required_params=["username", "service", "repository"],
        optional_params=["branch", "sha"],
        is_private=True,
    ),
    EndpointName.FLAGS: Command(
        required_params=["username", "service", "repository"],
        optional_params=["page", "page_size"],
        is_private=True,
    ),
    EndpointName.COVERAGE_TRENDS: Command(
        required_params=["username", "service", "repository", "flag"],
        optional_params=[
            "branch",
            "page",
            "page_size",
            "end_date",
            "interval",
            "start_date",
        ],
        is_private=True,
    ),
    EndpointName.COMPARISON: Command(
        required_params=["username", "service", "repository"],
        optional_params=["pullid", "base", "head"],
        is_private=True,
    ),
    EndpointName.COMPONENT_COMPARISON: Command(
        required_params=["username", "service", "repository"],
        optional_params=["pullid", "base", "head"],
        is_private=True,
    ),
    EndpointName.FILE_COMPARISON: Command(
        required_params=["username", "service", "repository", "path"],
        optional_params=["pullid", "base", "head"],
        is_private=True,
    ),
    EndpointName.FLAG_COMPARISON: Command(
        required_params=["username", "service", "repository"],
        optional_params=["pullid", "base", "head"],
        is_private=True,
    ),
    EndpointName.COVERAGE_TREND: Command(
        required_params=["username", "service", "repository"],
        optional_params=[
            "branch",
            "page",
            "page_size",
            "end_date",
            "start_date",
            "interval",
        ],
        is_private=True,
    ),
    EndpointName.FILE_COVERAGE_REPORT: Command(
        required_params=["username", "service", "repository", "path"],
        optional_params=["branch", "sha"],
        is_private=True,
    ),
    EndpointName.COMMIT_COVERAGE_REPORT: Command(
        required_params=["username", "service", "repository"],
        optional_params=["branch", "component_id", "flag", "path", "sha"],
        is_private=True,
    ),
    EndpointName.COMMIT_COVERAGE_TOTALS: Command(
        required_params=["username", "service", "repository"],
        optional_params=["branch", "component_id", "flag", "path", "sha"],
        is_private=True,
    ),
    EndpointName.NOTIFICATION: Command(
        required_params=["username", "service", "repository"],
    ),
}

service_mapping = {
    "gh": "github",
    "github": "github",
    "bb": "bitbucket",
    "bitbucket": "bitbucket",
    "gl": "gitlab",
    "gitlab": "gitlab",
}


def validate_service(service):
    normalized_name = service_mapping.get(service.lower())
    if normalized_name is None:
        raise ValueError(
            "Invalid service. valid services are: github, bitbucket, gitlab"
        )

    return normalized_name


def extract_command_params(command, command_name):
    params_dict = {}
    command_text = command["text"].split(" ")

    for param in command_text:
        if "=" not in param:
            continue

        params_dict[param.split("=")[0]] = param.split("=")[1]

    command = endpoint_mapping.get(command_name)
    command.validate(params_dict)

    return params_dict


def extract_optional_params(params_dict, command_name):
    endpoint = endpoint_mapping.get(command_name)

    if not bool(endpoint.optional_params):
        return {}

    optional_params = {}

    for key in endpoint.optional_params:
        if key in params_dict:
            optional_params[key] = params_dict.get(key)

    return optional_params


def format_nested_keys(data, formatted_data):
    for res in data["results"]:
        for key in res:
            formatted_data += f"*{key.capitalize()}*: {res[key]}\n"
        formatted_data += "------------------\n"
    return formatted_data


def validate_comparison_params(params_dict):
    base = params_dict.get("base")
    head = params_dict.get("head")
    pull_id = params_dict.get("pullid")
    if (not base or not head) and (not pull_id):
        raise Exception(
            "Comparison requires both a base and head parameter or a pullid parameter"
        )


def validate_notification_params(comparison, repo, owner):
    if not repo or not owner or not comparison:
        raise ValueError(
            "Comparison requires a repository, owner and comparison parameter"
        )


def channel_exists(client, channel_id):
    try:
        response = client.conversations_list(
            types="public_channel,private_channel"
        )
        channels = response["channels"]
        for channel in channels:
            if channel["id"] == channel_id:
                return True
        return False
    except SlackApiError as e:
        print(f"Error: {e.response['error']}")
def get_or_create_notifications(data):
    notification, created = Notification.objects.get_or_create(
        repo=data["name"],
        owner=data["author"]["name"],
        bot_token=data["slack__bot_token"],
    )
    channel_id = data["slack__channel_id"]

    if notification.channels:
        print(notification.channels, "channel_id", channel_id, flush=True)
        if channel_id in notification.channels:
            return f"Notification already enabled for {data['name']} in this channel 👀"

        notification.channels.append(channel_id)

    else:
        notification.channels = [channel_id]

    notification.save()
    return f"Notifications for {data['name']} enabled in this channel 📳."
