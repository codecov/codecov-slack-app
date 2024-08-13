import json
import logging
import os

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from core.enums import EndpointName
from core.helpers import (bot_is_member_of_channel, configure_notification,
                          send_not_member_response)
from core.models import SlackBot, SlackInstallation
from service_auth.models import SlackUser

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
        state_cookie_name="state",
    ),
)


@app.command("/codecov")
def handle_codecov_commands(ack, command, say, client):
    ack()

    command_text = command["text"].strip().split(" ")[0]
    response_url = command["response_url"]

    is_member = bot_is_member_of_channel(client, command["channel_id"])

    if not is_member:
        send_not_member_response(response_url)

    message_payload = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Invalid command or no input provided.\n*Need some help?*",
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
            case "coverage-trends":
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
                resolve_help(command["channel_id"], command["user_id"], client)
            case _:
                client.chat_postEphemeral(
                    channel=command["channel_id"],
                    user=command["user_id"],
                    blocks=message_payload,
                )

    except Exception as e:
        logger.error(f"Error processing command: {e}")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="There was an error processing your request. Please try again later.",
        )


@app.action("help-message")
def handle_help_message(ack, body, client):
    ack()

    channel_id = body["channel"]["id"]
    user_id = body["user"]["id"]

    resolve_help(channel_id, user_id, client)


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
                "text": "👇 Here are the list of the commands you can use:",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Auth commands:*\n`/codecov login` - Login to a service\n`/codecov logout` - Logout of current active service\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Users commands:*\n`/codecov organizations` - Get a list of organizations that user has access to\n`/codecov owner username=<org_name> service=<service>` - Get owner's information\n`/codecov users username=<org_name> service=<service>` Optional params: `is_admin=<is_admin> activated=<activated> page=<page> page_size=<page_size>` - Get a list of users for the specified owner\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Repositories commands:*\n`/codecov repos username=<org_name> service=<service>` Optional params: `names=<names> active=<active> page=<page> page_size=<page_size>` - Get a list of repos for the specified owner\n`/codecov repo repository=<repository> username=<org_name> service=<service>` - Get repo information\n`/codecov repo-config username=<org_name> service=<service> repository=<repository>` - Get the repository configuration for the specified owner and repository\n",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Branches commands:*\n`/codecov branches username=<org_name> service=<service> repository=<repository>` Optional params: `ordering=<ordering> author=<author> page=<page> page_size=<page_size>` - Get a list of branches for the repository\n`/codecov branch repository=<repository> username=<org_name> service=<service> branch=<branch>` - Get branch information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Commits commands:*\n`/codecov commits username=<org_name> service=<service> repository=<repository>` Optional params: `branch=<branch> page=<page> page_size=<page_size>` - Get a list of commits for the repository\n`/codecov commit repository=<repository> username=<org_name> service=<service> commitid=<commitid>` - Get commit information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Pulls commands:*\n`/codecov pulls username=<org_name> service=<service> repository=<repository>` Optional params: `ordering=<ordering> page=<page> page_size=<page_size> state=<closed,open,merged>` - Get a list of pulls for the repository\n`/codecov pull repository=<repository> username=<org_name> service=<service> pullid=<pullid>` - Get pull information\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Components commands:*\n`/codecov components username=<org_name> service=<service> repository=<repository>` Optional params: `branch=<branch> sha=<sha>` - Gets a list of components for the specified repository\n\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Flags commands:*\n`/codecov flags username=<org_name> service=<service> repository=<repository>` Optional params: `page=<page> page_size=<page_size>` - Gets a paginated list of flags for the specified repository\n`/codecov coverage-trends username=<org_name> service=<service> repository=<repository> flag=<flag>` Optional params: `page=<page> page_size=<page_size> start_date=<start_date> end_date=<end_date> branch=<branch> interval=<1d,30d,7d>`- Gets a paginated list of timeseries measurements aggregated by the specified interval\n\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Comparison commands:*\n `/codecov compare username=<org_name> service=<service> repository=<repository>` - Get a comparison between two commits or a pull and its base\n`/codecov compare-component username=<org_name> service=<service> repository=<repository>` - Gets a component comparison\n`/codecov compare-file username=<org_name> service=<service> repository=<repository> path=<path>` - Gets a comparison for a specific file path\n`/codecov compare-flag username=<org_name> service=<service> repository=<repository>` - Get a flag comparison\n\n _*NOTE*_\n _You must either pass `pullid=<pullid>` or both of `head=<head> base=<base>` in the comparison commands_\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Coverage commands:*\n`/codecov coverage-trend username=<org_name> service=<service> repository=<repository>` Optional params: `branch=<branch> end_date=<end_date> start_date=<start_date> interval=<1d,30d,7d> page=<page> page_size=<page_size>` - Get a paginated list of timeseries measurements aggregated by the specified interval\n`/codecov file-coverage-report repository=<repository> username=<org_name> service=<service> path=<path>` Optional params: `branch=<branch> sha=<sha>` - Get coverage info for a single file specified by path\n`/codecov commit-coverage-report repository=<repository> username=<org_name> service=<service>` Optional params: `path=<path> branch=<branch> sha=<sha> component_id=<component_id> flag=<flag>` - Get line-by-line coverage info (hit=0/miss=1/partial=2)\n`/codecov commit-coverage-totals repository=<repository> username=<org_name> service=<service> path=<path>` Optional params: `path=<path> branch=<branch> sha=<sha> component_id=<component_id> flag=<flag>` - Get the coverage totals for a given commit and the coverage totals broken down by file\n",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Notifications commands 📳*:\n`/codecov notify username=<org_name> service=<service> repository=<repository>` - Direct Notifications for a specific repo to a specific channel\n`/codecov notify-off username=<org_name> service=<service> repository=<repository>` - Turn off Notifications for a specific repo in a specific channel\n",
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

        # Delete users data
        SlackUser.objects.filter(team_id=body["team_id"]).delete()


@app.action("view-pr")
def handle_view_pr(ack, body, client, logger):
    ack()
    logger.info(body)
