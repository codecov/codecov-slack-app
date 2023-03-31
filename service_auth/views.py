import base64
import datetime
import os

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Service, SlackUser
from .helpers import validate_gh_call_params, get_github_user
from .actions import create_new_codecov_access_token

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI")

class GithubCallbackView(APIView):
    """
    Callback endpoint for github authentication flow
    """
    def get(self, request, format=None):
        provider = "github"
        # Get the authorization code from the GitHub's callback request
        code = request.GET.get("code")
        state = request.GET.get("state")
        user_id = base64.b64decode(state).decode("utf-8")
        
        validate_gh_call_params(code, state)

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

        access_token = response.json().get("access_token")
        if not access_token:
            return Response({"detail": "Error: No access token received from GitHub"}, status=400)

        service_userid, service_username = get_github_user(access_token)
        if not service_userid or not service_username:
            return Response({"detail": "Error: Could not get user info from GitHub"}, status=400)

        user = SlackUser.objects.filter(user_id=user_id).first()
        if not user:
            return Response({"detail": "Slack user not found"}, status=404)

        service = Service.objects.filter(user=user, name=(provider,)).first()
        if not service:
            service = Service(
                user=user,
            )
            service.name = (provider,)

        service.service_userid = service_userid
        service.service_username = service_username
        service.updated_at = datetime.datetime.now()
        service.active = True

        service.save()

        create_new_codecov_access_token(user)
        return Response({"detail": "You have successfully logged in"}, status=200)
