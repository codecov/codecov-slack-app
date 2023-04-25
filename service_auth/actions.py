import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict

import jwt
import requests
from slack_sdk.errors import SlackApiError
import urllib.parse

from .models import SlackUser

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_SCOPES = os.environ.get("GITHUB_SCOPES", "repo").split(",")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI")
CODECOV_SECRET = os.environ.get("CODECOV_SECRET")
USER_ID_SECRET = os.environ.get("USER_ID_SECRET")
CODECOV_PUBLIC_API = os.environ.get("CODECOV_PUBLIC_API")


@dataclass
class Endpoint:
    url: str
    is_private: bool


class EndpointName(Enum):
    SERVICE_OWNERS = "service_owners"
    OWNER = "owner"
    USERS_LIST = "users_list"


def get_endpoint_details(
    endpoint_name: EndpointName,
    service=None,
    owner_username=None,
    repository=None,
    params=None,
) -> Endpoint:
    params_str = urllib.parse.urlencode(params)

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
    }

    endpoint = endpoints_map[endpoint_name]
    if params_str:
        print(params_str, flush=True)
        endpoint.url = f"{endpoint.url}?{params_str}"

    return endpoint


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


def verify_codecov_access_token(slack_user: SlackUser):
    owner = slack_user.active_service.service_username
    service = slack_user.active_service.name
    codecov_access_token = slack_user.codecov_access_token
    url = f"{CODECOV_PUBLIC_API}/{service}/{owner}"
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {codecov_access_token}",
    }

    response = requests.get(url, headers=headers)
    return response.status_code == 200


def get_or_create_slack_user(user_info):
    user_id = user_info["user"]["id"]
    current_user = SlackUser.objects.filter(user_id=user_id).first()

    if not current_user:
        user_info = _user_info(user_info)
        (
            username,
            email,
            display_name,
            team_id,
            is_bot,
            is_owner,
            is_admin,
        ) = user_info.values()

        current_user = SlackUser.objects.create(
            user_id=user_id,
            username=username,
            email=email,
            team_id=team_id,
            is_bot=is_bot,
            display_name=display_name,
            is_owner=is_owner,
            is_admin=is_admin,
        )
    return current_user


def create_new_codecov_access_token(slack_user: SlackUser):
    request_url = "http://api.codecov.io/internal/slack/generate-token/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {CODECOV_SECRET}",
    }
    data = {
        "username": slack_user.active_service.service_username,
        "service": slack_user.active_service.name,
    }
    response = requests.post(request_url, headers=headers, data=data)

    if response.status_code == 200:
        data = response.json()
        slack_user.codecov_access_token = data.get("token")
        slack_user.save()
    else:
        raise Exception("Error creating codecov access token")


def authenticate_command(client, command):
    slack_user_id = command["user_id"]
    user_info = client.users_info(user=slack_user_id)
    slack_user = get_or_create_slack_user(user_info)

    codecov_access_token = slack_user.codecov_access_token
    if codecov_access_token:
        verified = verify_codecov_access_token(slack_user)
        if not verified:
            create_new_codecov_access_token(slack_user)
        return

    view_login_modal(client, command)


def view_login_modal(
    client, command
):  # this will be used to override the active provider using /login
    slack_user_id = command["user_id"]
    slack_user_id_jwt = jwt.encode(
        {"user_id": slack_user_id}, USER_ID_SECRET, algorithm="HS256"
    )
    # we support gh flow at first
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_REDIRECT_URI}&scope={GITHUB_SCOPES}&state={slack_user_id_jwt}"

    client.views_open(
        trigger_id=command["trigger_id"],
        # A simple view payload for a modal
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "My App"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Login to access Codecov Public API",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Login via GitHub",
                        },
                        "url": github_auth_url,
                        "style": "primary",
                    },
                }
            ],
        },
    )


def handle_codecov_public_api_request(
    user_id, endpoint_name: EndpointName, service=None, owner_username=None, params=None
):
    slack_user = SlackUser.objects.filter(user_id=user_id).first()
    _service = service if service else slack_user.active_service.name

    endpoint_details = get_endpoint_details(
        endpoint_name, service=_service, owner_username=owner_username, params=params
    )

    if not endpoint_details:
        raise Exception("Endpoint not found")

    request_url = endpoint_details.url
    is_private = endpoint_details.is_private

    headers = {
        "accept": "application/json",
    }
    if is_private:
        codecov_access_token = slack_user.codecov_access_token
        headers["Authorization"] = f"Bearer {codecov_access_token}"

    response = requests.get(request_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
