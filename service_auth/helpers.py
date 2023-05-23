import os
import urllib.parse
from dataclasses import dataclass
from typing import Dict

import requests
from rest_framework.exceptions import ValidationError

from core.enums import EndpointName

CODECOV_PUBLIC_API = os.environ.get("CODECOV_PUBLIC_API")


def _user_info(user_info):
    username = user_info["user"]["name"]
    email = user_info["user"]["profile"]["email"]
    display_name = user_info["user"]["profile"]["display_name"]
    team_id = user_info["user"]["team_id"]
    is_bot = user_info["user"]["is_bot"]
    is_owner = user_info["user"]["is_owner"]
    is_admin = user_info["user"]["is_admin"]

    return {
        "username": username,
        "email": email,
        "display_name": display_name,
        "team_id": team_id,
        "is_bot": is_bot,
        "is_owner": is_owner,
        "is_admin": is_admin,
    }


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
class Endpoint:  # keeping this here for now
    url: str


def get_endpoint_details(
    endpoint_name: EndpointName,
    service=None,
    params_dict: Dict = None,
    optional_params=None,
) -> Endpoint:
    owner_username = params_dict.get("username")
    repository = params_dict.get("repository")
    branch = params_dict.get("branch")
    commit_id = params_dict.get("commitid")
    pull_id = params_dict.get("pullid")
    flag = params_dict.get("flag")
    file_path = params_dict.get("path")

    endpoints_map: Dict[EndpointName, Endpoint] = {
        EndpointName.SERVICE_OWNERS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/",
        ),
        EndpointName.OWNER: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/",
        ),
        EndpointName.USERS_LIST: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/users/",
        ),
        EndpointName.REPO_CONFIG: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/config/",
        ),
        EndpointName.REPOS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/",
        ),
        EndpointName.REPO: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/",
        ),
        EndpointName.BRANCHES: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/branches/",
        ),
        EndpointName.BRANCH: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/branches/{branch}/",
        ),
        EndpointName.COMMITS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/commits/",
        ),
        EndpointName.COMMIT: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/commits/{commit_id}/",
        ),
        EndpointName.PULLS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/pulls/",
        ),
        EndpointName.PULL: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/pulls/{pull_id}/",
        ),
        EndpointName.COMPONENTS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/components/",
        ),
        EndpointName.FLAGS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/flags/",
        ),
        EndpointName.COVERAGE_TRENDS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/flags/{flag}/coverage/",
        ),
        EndpointName.COMPARISON: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/compare/",
        ),
        EndpointName.COMPONENT_COMPARISON: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/compare/components/",
        ),
        EndpointName.FILE_COMPARISON: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/compare/file/{file_path}/",
        ),
        EndpointName.FLAG_COMPARISON: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/compare/flags/",
        ),
        EndpointName.COVERAGE_TREND: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/coverage/",
        ),
        EndpointName.FILE_COVERAGE_REPORT: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/file_report/{file_path}/",
        ),
        EndpointName.COMMIT_COVERAGE_REPORT: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/report/",
        ),
        EndpointName.COMMIT_COVERAGE_TOTALS: Endpoint(
            url=f"{CODECOV_PUBLIC_API}/{service}/{owner_username}/repos/{repository}/totals/",
        ),
    }

    endpoint = endpoints_map[endpoint_name]

    if optional_params:
        params_str = urllib.parse.urlencode(optional_params)
        endpoint.url = f"{endpoint.url}?{params_str}"

    return endpoint
