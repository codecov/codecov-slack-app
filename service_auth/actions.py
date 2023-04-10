import ast
import base64
import os

import requests

from .models import SlackUser

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_SCOPES = os.environ.get("GITHUB_SCOPES", "repo").split(",")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI")
CODECOV_SECRET = os.environ.get("CODECOV_SECRET")


def _user_info(user_info):
    username = user_info["user"]["name"]
    email = user_info["user"]["profile"]["email"]
    display_name = user_info["user"]["profile"]["display_name"]
    team_id = user_info["user"]["team_id"]
    is_bot = user_info["user"]["is_bot"]
    is_owner = user_info["user"]["is_owner"]
    is_admin = user_info["user"]["is_admin"]

    return username, email, display_name, team_id, is_bot, is_owner, is_admin


def verify_codecov_access_token(slack_user):
    owner = slack_user.active_service.service_username
    service = slack_user.active_service.name
    service_name = ast.literal_eval(service)[0]
    codecov_access_token = slack_user.codecov_access_token
    url = f"https://api.codecov.io/api/v2/{service_name}/{owner}"
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
        (
            username,
            email,
            display_name,
            team_id,
            is_bot,
            is_owner,
            is_admin,
        ) = _user_info(user_info)
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


def create_new_codecov_access_token(slack_user):
    request_url = "http://api.codecov.io/internal/slack/generate-token/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {CODECOV_SECRET}",
        "username": slack_user.username,
        "service": slack_user.active_service.name,
    }
    response = requests.post(request_url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        slack_user.codecov_access_token = data.get("token")
        slack_user.save()
    else:
        raise Exception("Error creating codecov access token")


def handle_private_endpoints(client, command):
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
    slack_user_id_b64 = base64.urlsafe_b64encode(
        slack_user_id.encode()
    ).decode()
    # we support gh flow at first
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={GITHUB_REDIRECT_URI}&scope={GITHUB_SCOPES}&state={slack_user_id_b64}"

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
