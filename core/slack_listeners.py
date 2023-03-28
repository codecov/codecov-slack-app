import logging
import os

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from .slack_datastores import DjangoInstallationStore, DjangoOAuthStateStore
from service_auth.helpers import force_login

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


@app.command("/hello_world")
def hello_world(ack, say):
    ack()
    say("Hello world!")


@app.command("/test_gh_login")
def test_gh_login(ack, command, say, client):
    ack()
    # check if api endpoint requested is private or public
    # if private, check if user is logged in / force login
    force_login(client, command)
    say("You're logged in!----")