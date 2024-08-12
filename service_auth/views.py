import os

import jwt
import requests
from django.shortcuts import redirect
from rest_framework.response import Response
from rest_framework.views import APIView

from .actions import create_new_codecov_access_token
from .helpers import get_github_user, notify_user, validate_gh_call_params
from .models import Service, SlackUser

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI")
USER_ID_SECRET = os.environ.get("USER_ID_SECRET")
SLACK_APP_ID = os.environ.get("SLACK_APP_ID")


class GithubCallbackView(APIView):
    """
    Callback endpoint for github authentication flow
    """

    def get(self, request, format=None):
        provider = "github"
        # Get the authorization code from the GitHub's callback request
        code = request.GET.get("code")
        state = request.GET.get("state")
        validate_gh_call_params(code, state)

        user_id_state = state.split("-")[0]
        user_id = jwt.decode(
            user_id_state, USER_ID_SECRET, algorithms=["HS256"]
        )["user_id"]
        channel_id = state.split("-")[1]

        # Exchange the authorization code for an access token
        headers = {"Accept": "application/json"}
        data = {
            "code": code,
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "redirect_uri": GITHUB_REDIRECT_URI,
        }
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers=headers,
            data=data,
        )
        if response.status_code != 200:
            return Response(
                {"detail": "Error: Could not get access token from GitHub"},
                status=400,
            )
        access_token = response.json().get("access_token")
        if not access_token:
            return Response(
                {"detail": "Error: No access token received from GitHub"},
                status=400,
            )

        service_userid, service_username = get_github_user(access_token)
        if not service_userid or not service_username:
            return Response(
                {"detail": "Error: Could not get user info from GitHub"},
                status=400,
            )

        user = SlackUser.objects.filter(user_id=user_id).first()
        if not user:
            return Response(
                {"detail": f"Slack user not found {user_id}"}, status=404
            )

        service = Service.objects.filter(user=user, name=provider).first()
        if not service:
            service = Service(
                user=user,
            )
            service.name = provider

        service.service_userid = service_userid
        service.service_username = service_username
        service.active = True

        service.save()

        # create new codecov access token
        try:
            create_new_codecov_access_token(user)
        except Exception as e:
            message = "Error creating Codecov access token, are you sure you have a Codecov account?"
            error = notify_user(user, channel_id, message=message)
            if error:
                return error

            return Response(
                {"detail": "Error creating Codecov access token"}, status=400
            )

        # redirect to slack app
        team_id = user.team_id
        slack_url = f"https://slack.com/app_redirect?app={SLACK_APP_ID}&channel={channel_id}&team={team_id}"

        message = "Successfully connected your GitHub account to Codecov! You can now use Codecov commands in this channel."
        notify_user(user, channel_id, message=message)
        return redirect(slack_url)
