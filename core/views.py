import logging

from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from core.authentication import InternalTokenAuthentication
from core.helpers import (channel_exists, format_comparison,
                          validate_notification_params)
from core.models import Notification
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
            return Response({"detail": "No notifications found"}, status=404)

        for notification in notifications:
            client = WebClient(token=notification.installation.bot_token)
            for channel in notification.channels:
                if not channel_exists(client, channel_id=channel):
                    Logger.warning(
                        f"Channel {channel} does not exist in workspace {notification.installation.bot_token}"
                    )
                    continue

                try:
                    blocks = format_comparison(comparison)
                    client.chat_postMessage(
                        channel=channel,
                        text="",
                        blocks=blocks,
                    )
                except SlackApiError as e:
                    print(e, flush=True)
                    assert e.response["ok"] is False
                    assert e.response["error"]
                    print(f"Got an error: {e.response['error']}")
                    return Response(
                        {"detail": f"Error posting message, {e.response["error"]}, {blocks}"}, status=500
                    )
        return Response({"detail": "Message posted!"}, status=200)
