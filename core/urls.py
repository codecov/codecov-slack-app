from django.http import HttpRequest
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from slack_bolt.adapter.django import SlackRequestHandler

from .slack_listeners import app
from .views import NotificationView, health, slack_install

handler = SlackRequestHandler(app=app)


@csrf_exempt
def slack_events_handler(request: HttpRequest):
    return handler.handle(request)


def slack_oauth_handler(request: HttpRequest):
    return handler.handle(request)


urlpatterns = [
    path("slack/events", slack_events_handler, name="handle"),
    path("slack/install", slack_install, name="install"),
    path("slack/oauth_redirect", slack_oauth_handler, name="oauth_redirect"),
    path("notify", NotificationView.as_view(), name="notify"),
    path("health", health, name="health"),
]
