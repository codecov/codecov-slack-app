from dataclasses import dataclass
from typing import Dict, Optional

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
    EndpointName.SERVICE_OWNERS.value: Command(is_private=True),
    EndpointName.OWNER.value: Command(
        required_params=["username", "service"],
    ),
    EndpointName.USERS_LIST.value: Command(
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
    EndpointName.REPO_CONFIG.value: Command(
        required_params=["username", "service", "repository"],
        is_private=True,
    ),
    EndpointName.REPOS.value: Command(
        required_params=["username", "service"],
        optional_params=["active", "names", "search", "page", "page_size"],
    ),
    EndpointName.REPO.value: Command(
        required_params=["username", "service", "repository"],
    ),
    EndpointName.BRANCHES.value: Command(
        required_params=["username", "service", "repository"],
        optional_params=["author", "ordering", "page", "page_size"],
        is_private=True,
    ),
    EndpointName.BRANCH.value: Command(
        required_params=["username", "service", "repository", "branch"],
        is_private=True,
    ),
    EndpointName.COMMITS.value: Command(
        required_params=["username", "service", "repository"],
        optional_params=["branch", "page", "page_size"],
        is_private=True,
    ),
    EndpointName.COMMIT.value: Command(
        required_params=["username", "service", "repository", "commitid"],
        is_private=True,
    ),
    EndpointName.PULLS.value: Command(
        required_params=["username", "service", "repository"],
        optional_params=["ordering", "page", "page_size", "state"],
        is_private=True,
    ),
    EndpointName.PULL.value: Command(
        required_params=["username", "service", "repository", "pullid"],
        is_private=True,
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


def extract_command_params(command):
    params_dict = {}
    command_text = command["text"].split(" ")

    for param in command_text:
        if "=" not in param:
            continue

        params_dict[param.split("=")[0]] = param.split("=")[1]

    command = endpoint_mapping.get(command_text[0])
    command.validate(params_dict)

    return params_dict


def extract_optional_params(params_dict, command):
    command_text = command["text"].split(" ")[0]
    endpoint = endpoint_mapping[command_text]

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
