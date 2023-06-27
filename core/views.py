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
                url = comparison.get("url")
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

                    if not created:
                        client.chat_update(
                            channel=channel,
                            ts=notification_status.message_timestamp,
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
