import json
import logging
import os

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from core.enums import EndpointName
from core.helpers import configure_notification
from core.models import SlackBot, SlackInstallation

from .resolvers import (BranchesResolver, BranchResolver, CommitCoverageReport,
                        CommitCoverageTotals, CommitResolver, CommitsResolver,
                        ComparisonResolver, ComponentsResolver,
                        CoverageTrendResolver, CoverageTrendsResolver,
                        FileCoverageReport, FlagsResolver,
                        NotificationResolver, OrgsResolver, OwnerResolver,
                        PullResolver, PullsResolver, RepoConfigResolver,
                        RepoResolver, ReposResolver, UsersResolver,
                        resolve_help, resolve_service_login,
                        resolve_service_logout)
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

    try:
        match command_text:
            case "login":
                resolve_service_login(client, command, say)
            case "logout":
                resolve_service_logout(client, command, say)
            case "organizations":
                OrgsResolver(client, command, say)()
            case "owner":
                OwnerResolver(client, command, say)()
            case "users":
                UsersResolver(client, command, say)()
            case "repo-config":
                RepoConfigResolver(client, command, say)()
            case "repos":
                ReposResolver(client, command, say)()
            case "repo":
                RepoResolver(client, command, say)()
            case "branches":
                BranchesResolver(client, command, say)()
            case "branch":
                BranchResolver(client, command, say)()
            case "commits":
                CommitsResolver(client, command, say)()
            case "commit":
                CommitResolver(client, command, say)()
            case "pulls":
                PullsResolver(client, command, say)()
            case "pull":
                PullResolver(client, command, say)()
            case "components":
                ComponentsResolver(client, command, say)()
            case "flags":
                FlagsResolver(client, command, say)()
            case "coverage-trends":  # use endpoint enum for cases
                CoverageTrendsResolver(client, command, say)()
            case "compare":
                ComparisonResolver(
                    client, command, say, command_name=EndpointName.COMPARISON
                )()
            case "compare-component":
                ComparisonResolver(
                    client,
                    command,
                    say,
                    command_name=EndpointName.COMPONENT_COMPARISON,
                )()
            case "compare-file":
                ComparisonResolver(
                    client,
                    command,
                    say,
                    command_name=EndpointName.FILE_COMPARISON,
                )()
            case "compare-flag":
                ComparisonResolver(
                    client,
                    command,
                    say,
                    command_name=EndpointName.FLAG_COMPARISON,
                )()
            case "coverage-trend":
                CoverageTrendResolver(client, command, say)()
            case "commit-coverage-report":
                CommitCoverageReport(client, command, say)()
            case "commit-coverage-totals":
                CommitCoverageTotals(client, command, say)()
            case "file-coverage-report":
                FileCoverageReport(client, command, say)()
            case "notify":
                NotificationResolver(command, client, say, notify=True)()
            case "notify-off":
                NotificationResolver(command, client, say)()
            case "help":
                resolve_help(say)
            case _:
                say(text="", blocks=message_payload)

    except Exception as e:
        logger.error(e)
        say(
            "There was an error processing your request. Please try again later."
        )


@app.action("help-message")
def handle_help_message(ack, say):
    ack()
    resolve_help(say)


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    home_tab_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ":rocket: *Welcome to Codecov Slack App* :rocket:\n\nTake control of your notifications and streamline your workflow. With just a few simple commands, you can enhance collaboration across multiple channels and repositories. Here's what you can do:",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "1. Interact with Codecov Public API:\n- Explore the full potential of our app by interacting with Codecov public API. Simply use the `/codecov help` command to discover available features and commands.",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "2. Redirect Notifications to Multiple Channels:\n- Use the command `/codecov notify` to effortlessly redirect notifications from multiple repositories to designated channels.",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "3. Public Repo PR Notifications without Authentication:\n- No need to authenticate with external providers! With our app, you can receive notifications for pull requests from public repositories directly in Slack. Stay informed and collaborate seamlessly with your team.",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "4. Access Private Data with Provider Authentication:\n- For more advanced commands that require access to private data, we've got you covered. Currently supporting GitHub authentication, you can securely connect your account to unlock additional functionalities and ensure data privacy using `/codecov login`.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Learn more about the Codecov API here:\n"
                "<https://docs.codecov.io/reference|https://docs.codecov.io/reference>",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "Have questions or need assistance? Reach out to our friendly support team on https://codecov.freshdesk.com/support/home.",
                }
            ],
        },
    ]

    client.views_publish(
        user_id=event["user"], view={"type": "home", "blocks": home_tab_blocks}
    )


@app.action("close-modal")
def handle_close_modal(ack, body, client):
    response = {
        "response_action": "update",
        "view": {
            "type": "modal",
            "title": {"type": "plain_text", "text": "Codecov App"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "You can close this modal now!",
                    },
                }
            ],
        },
    }

    response["view"]["close"] = {"type": "plain_text", "text": "Done"}
    client.views_update(
        view_id=body["view"]["id"],
        hash=body["view"]["hash"],
        view=response["view"],
    )
    ack(response)


@app.action("approve-notification")
def handle_approve_notification(ack, body, client, logger):
    ack()
    logger.info(body)
    data = json.loads(body["view"]["private_metadata"])
    message = configure_notification(data)

    client.views_update(
        view_id=body["view"]["id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Codecov Notification"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message},
                }
            ],
        },
    )


@app.action("decline-notification")
def handle_decline_notification(ack, body, client, logger):
    ack()
    logger.info(body)
    client.views_update(
        view_id=body["view"]["id"],
        view={
            "type": "modal",
            "title": {"type": "plain_text", "text": "Codecov Notification"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Notification declined. You can safely close this modal.",
                    },
                }
            ],
        },
    )


@app.event("app_uninstalled")
def handle_app_uninstalled(body, logger):
    logger.info(body)
    event = body.get("event")
    if event:
        logger.info(event)
        logger.info("App was uninstalled, removing installation data")

        # Delete workspace installation data
        SlackInstallation.objects.filter(team_id=body["team_id"]).delete()

        # Delete workspace bot data
        SlackBot.objects.filter(team_id=body["team_id"]).delete()


@app.action("view-pr")
def handle_view_pr(ack, body, client, logger):
    ack()
    logger.info(body)
