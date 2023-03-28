import base64
import os

from .models import SlackUser

gh_client_id = os.environ.get("GITHUB_CLIENT_ID")
gh_client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
gh_scopes = os.environ.get("GITHUB_SCOPES", "repo").split(",")
gh_redirect_uri = os.environ.get("GITHUB_REDIRECT_URI")


def _user_info(user_info):
    username = user_info["user"]["name"]
    email = user_info["user"]["profile"]["email"]
    display_name = user_info["user"]["profile"]["display_name"]
    team_id = user_info["user"]["team_id"]
    is_bot = user_info["user"]["is_bot"]
    is_owner = user_info["user"]["is_owner"]
    is_admin = user_info["user"]["is_admin"]

    return username, email, display_name, team_id, is_bot, is_owner, is_admin


def verify_codecov_access_token(codecov_access_token):
    return  # if codecov_access_token exists in user DB


def get_codecov_access_token(user_info):
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
    return current_user.codecov_access_token 


def force_login(client, command):
    slack_user_id = command["user_id"]

    user_info = client.users_info(user=slack_user_id)
    codecov_access_token = get_codecov_access_token(user_info)

    if codecov_access_token:
        verified = verify_codecov_access_token(codecov_access_token)

        if verified:
            return
        else:
            # create a new codecov access token using the current service_user_id
            return

    slack_user_id_b64 = base64.urlsafe_b64encode(
        slack_user_id.encode()
    ).decode()
    github_auth_url = f"https://github.com/login/oauth/authorize?client_id={gh_client_id}&redirect_uri={gh_redirect_uri}&scope={gh_scopes}&state={slack_user_id_b64}"

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

