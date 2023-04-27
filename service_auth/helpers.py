import os
import urllib.parse
from dataclasses import dataclass
from typing import Dict

import requests
from rest_framework.exceptions import ValidationError

from core.enums import EndpointName

CODECOV_PUBLIC_API = os.environ.get("CODECOV_PUBLIC_API")


def validate_gh_call_params(code, state):
    if not code:
        raise ValidationError("Missing code parameter")
    if not state:
        raise ValidationError("Missing state parameter")


def get_github_user(access_token):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("id"), data.get("login")
    else:
        return None, None


@dataclass
class Endpoint:
    url: str
    is_private: bool


def get_endpoint_details(
    endpoint_name: EndpointName,
    service=None,
    params_dict: Dict = None,
    optional_params=None,
) -> Endpoint:
    owner_username = params_dict.get("username")
    repository = params_dict.get("repository")
    branch = params_dict.get("branch")

    endpoints_map: Dict[EndpointName, Endpoint] = {
        EndpointName.SERVICE_OWNERS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/",
            is_private=True,
        ),
        EndpointName.OWNER: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/",
            is_private=False,
        ),
        EndpointName.USERS_LIST: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/users/",
            is_private=True,
        ),
        EndpointName.REPO_CONFIG: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/config/",
            is_private=True,
        ),
        EndpointName.REPOS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/",
            is_private=False,
        ),
        EndpointName.REPO: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/",
            is_private=False,
        ),
        EndpointName.BRANCHES: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/branches/",
            is_private=True,
        ),
        EndpointName.BRANCH: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/branches/{branch}/",
            is_private=True,
        ),
    }

    endpoint = endpoints_map[endpoint_name]

    if optional_params:
        params_str = urllib.parse.urlencode(optional_params)
        endpoint.url = f"{endpoint.url}?{params_str}"

    return endpoint
