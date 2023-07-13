import logging
import os

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from slack_sdk import WebClient
from django.shortcuts import render

from core.authentication import InternalTokenAuthentication
from core.helpers import (format_comparison,
                          validate_notification_params)
from core.models import Notification, NotificationStatus
from core.permissions import InternalTokenPermissions
from core.slack_datastores import DjangoOAuthStateStore

Logger = logging.getLogger(__name__)

SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_SCOPES = os.environ.get("SLACK_SCOPES")
SLACK_REDIRECT_URI = os.environ.get("SLACK_REDIRECT_URI")

# Create your views here.
def health(request):
    return HttpResponse("Codecov Slack App is live!")


class NotificationView(APIView):
    """
    Handle comparison data from Codecov
    """

    authentication_classes = [InternalTokenAuthentication]
    permission_classes = [InternalTokenPermissions]

    def post(self, request, format=None):
        comparison = request.data.get("comparison")
        repo = request.data.get("repository")
        owner = request.data.get("owner")

        validate_notification_params(comparison, repo, owner)

        notifications = Notification.objects.filter(owner=owner, repo=repo)
        if not notifications.exists():
            return Response({"detail": "No notifications found"}, status=200)

        for notification in notifications:
            client = WebClient(token=notification.installation.bot_token)
            for channel in notification.channels:
                url = comparison.get("url") # TODO: we should not depend on the url being present to fetch the pullid
                if not url:
                    Logger.info(
                        "Comparison url is not present. Skipping notification"
                    )
                    continue

                pullid = url.split("/")[-1]

                if len(pullid) >= 40:
                    continue

                (
                    notification_status,
                    created,
                ) = NotificationStatus.objects.get_or_create(
                    notification=notification, pullid=pullid, channel=channel
                )

                try:
                    blocks = format_comparison(comparison)

                    if not created and notification_status.status == "success":
                        client.chat_update(
                            channel=channel,
                            ts=notification_status.message_timestamp,
                            text="",
                            blocks=blocks,
                            unfurl_media=False,
                            unfurl_links=False,
                        )

                        Logger.info(
                            f"Updated message for {pullid} in channel {channel}"
                        )

                    else:
                        response = client.chat_postMessage(
                            channel=channel,
                            text="",
                            blocks=blocks,
                            unfurl_media=False,
                            unfurl_links=False,
                        )
                        notification_status.message_timestamp = response["ts"]
                        notification_status.save()

                        Logger.info(
                            f"Posted message for {pullid} in channel {channel}"
                        )
                
                except Exception as e:
                    print(e, flush=True)

                    # Set notification status to error
                    notification_status.status = "error"
                    notification_status.save()

                    Logger.error(
                        f"Error posting message in {channel} for workspace {notification.installation.bot_token} {notification.installation.team_name}"
                    )

        return Response({"detail": "Notifications are completed successfully"}, status=200)


def slack_install(request):
    store = DjangoOAuthStateStore(
        expiration_seconds=120,
        logger=Logger,
    )
    state = store.issue()
    context = {
        "client_id": SLACK_CLIENT_ID,
        "scope": SLACK_SCOPES,
        "redirect_uri": SLACK_REDIRECT_URI,
        "state": state,
    }

    return render(request, "pages/slack_install.html", context)