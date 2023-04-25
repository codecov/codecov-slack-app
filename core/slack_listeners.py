import logging
import os

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from .resolvers import (resolve_help, resolve_organizations, resolve_owner,
                        resolve_service_login, resolve_service_logout, resolve_users)
from .slack_datastores import DjangoInstallationStore, DjangoOAuthStateStore

logger = logging.getLogger(__name__)
client_id, client_secret, signing_secret, scopes, user_scopes = (
    os.environ.get("SLACK_CLIENT_ID"),
    os.environ.get("SLACK_CLIENT_SECRET"),
    os.environ.get("SLACK_SIGNING_SECRET"),
    os.environ.get("SLACK_SCOPES", "commands").split(","),
    os.environ.get("SLACK_USER_SCOPES", "search:read").split(","),
)

app = App(
    signing_secret=signing_secret,
    oauth_settings=OAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
        user_scopes=user_scopes,
        # If you want to test token rotation, enabling the following line will make it easy
        # token_rotation_expiration_minutes=1000000,
        installation_store=DjangoInstallationStore(
            client_id=client_id,
            logger=logger,
        ),
        state_store=DjangoOAuthStateStore(
            expiration_seconds=120,
            logger=logger,
        ),
    ),
)


@app.command("/codecov")
def handle_codecov_commands(ack, command, say, client):
    ack()
    command_text = command["text"].split(" ")[0]

    try:
        if command_text == "login":
            resolve_service_login(client, command, say)
        elif command_text == "logout":
            resolve_service_logout(client, command, say)
        elif command_text == "organizations":
            resolve_organizations(client, command, say)
        elif command_text == "owner":
            resolve_owner(client, command, say)
        elif command_text == "users":
            resolve_users(client, command, say)
        elif command_text == "help":
            resolve_help(say)

        else:
            message_payload = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Invalid command.\n*Need some help?*",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Help",
                                "emoji": True,
                            },
                            "value": "help",
                            "action_id": "help-message",
                        }
                    ],
                },
            ]

            say(
                text="",
                blocks=message_payload,
            )

    except Exception as e:
        logger.error(e)
        say(
            "There was an error processing your request. Please try again later."
        )


@app.action("help-message")
def handle_help_message(ack, say):
    ack()
    resolve_help(say)
