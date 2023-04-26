from dataclasses import dataclass
from typing import Dict

from .enums import EndpointName


@dataclass
class Command:
    required_params: list
    optional_params: list


endpoint_mapping: Dict[EndpointName, Command] = {
    EndpointName.SERVICE_OWNERS.value: Command(
        required_params=[], optional_params=[]
    ),
    EndpointName.OWNER.value: Command(
        required_params=["username", "service"], optional_params=[]
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
    ),
    EndpointName.REPO_CONFIG.value: Command(
        required_params=["username", "service", "repository"],
        optional_params=[],
    ),
    EndpointName.REPOS.value: Command(
        required_params=["username", "service"],
        optional_params=["active", "names", "search", "page", "page_size"],
    ),
    EndpointName.REPO.value: Command(
        required_params=["username", "service", "repository"],
        optional_params=[],
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


def extract_command_params(command, say):
    params_dict = {}
    command_text = command["text"].split(" ")

    for param in command_text:
        if "=" not in param:
            continue

        params_dict[param.split("=")[0]] = param.split("=")[1]

    endpoint = endpoint_mapping.get(command_text[0])

    if endpoint.required_params is not None:
        if len(params_dict) == 0:
            raise ValueError(
                "Missing required parameters"
            )  # provide a help message

        for param in endpoint.required_params:
            if param not in params_dict:
                raise ValueError(f"Missing required parameter {param}")

    return params_dict


def extract_optional_params(params_dict, command):
    command_text = command["text"].split(" ")[0]
    endpoint = endpoint_mapping[command_text]

    if endpoint.optional_params is None:
        return {}

    optional_params = {}

    for key in endpoint.optional_params:
        if key in params_dict:
            optional_params[key] = params_dict.get(key)

    return optional_params
