import logging

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.authentication import InternalTokenAuthentication
from core.helpers import (channel_exists, format_comparison,
                          validate_notification_params)
from core.models import Notification, NotificationStatus
from core.permissions import InternalTokenPermissions

Logger = logging.getLogger(__name__)

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
                if not channel_exists(client, channel_id=channel):
                    Logger.warning(
                        f"Channel {channel} does not exist in workspace {notification.installation.bot_token}"
                    )
                    continue

                url = comparison.get("url")
                pullid = url.split("/")[-1]

                (
                    notification_status,
                    created,
                ) = NotificationStatus.objects.get_or_create(
                    notification=notification, pullid=pullid, channel=channel
                )

                try:
                    blocks = format_comparison(comparison)
                    if not created:
                        client.chat_update(
                            channel=channel,
                            ts=notification_status.message_ts,
                            text="",
                            blocks=blocks,
                        )

                        Logger.info(
                            f"Updated message for {pullid} in channel {channel}"
                        )

                    else:
                        response = client.chat_postMessage(
                            channel=channel,
                            text="",
                            blocks=blocks,
                        )
                        notification_status.message_ts = response["ts"]
                        notification_status.save()

                        Logger.info(
                            f"Posted message for {pullid} in channel {channel}"
                        )

                except SlackApiError as e:
                    print(e, flush=True)
                    assert e.response["ok"] is False
                    assert e.response["error"]
                    print(f"Got an error: {e.response['error']}")

                    # Set notification status to error
                    notification_status.status = "error"
                    notification_status.save()

                    return Response(
                        {"detail": "Error posting message"}, status=500
                    )

        return Response({"detail": "Message posted!"}, status=200)
