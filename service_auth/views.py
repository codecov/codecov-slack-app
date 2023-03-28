import base64
import datetime
import os

import requests
from django.http import HttpResponse
from .models import SlackUser, Service

gh_client_id = os.environ.get("GITHUB_CLIENT_ID")
gh_client_secret = os.environ.get("GITHUB_CLIENT_SECRET")
gh_redirect_uri = os.environ.get("GITHUB_REDIRECT_URI")


def get_github_user(access_token):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("id"), data.get("login")
    else:
        return None, None


def gh_callback(request):
    provider = "github"
    # Get the authorization code from the GitHub's callback request
    code = request.GET.get("code")
    state = request.GET.get("state")
    user_id = base64.b64decode(state).decode('utf-8')  # use this to get user id from DB

    # Exchange the authorization code for an access token
    headers = {"Accept": "application/json"}
    data = {
        "code": code,
        "client_id": gh_client_id,
        "client_secret": gh_client_secret,
        "redirect_uri": gh_redirect_uri,
    }
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers=headers,
        data=data,
    )

    # Parse the access token from the response and save it to DB
    access_token = response.json()["access_token"]
    if access_token:
        service_userid, service_username = get_github_user(access_token)
        if service_userid and service_username: 
            # Save the service user id and service username to DB
            user = SlackUser.objects.filter(user_id=user_id).first()
            service = Service.objects.filter(user=user, name=provider).first()

            if not service:
                new_service = Service(
                    user=user,
                )
                new_service.service_userid = service_userid
                new_service.name=provider,
                new_service.service_username = service_username
                new_service.save()

            else:
                service.service_userid = service_userid
                service.service_username = service_username
                service.updated_at = datetime.datetime.now()

                service.save()
            
            return HttpResponse("You have successfully logged in")
    # Step 5: Redirect the user to the desired page --> SLACK WORKSPACE PAGE
    return HttpResponse("You have successfully logged in")


# update the provider name to be in an enum -> use lower case too 
# make sure to handle create or update provider name 
# update the name of the service 
# make sure to handle other flows -> if user is not found, if service is not found, etc.
# maybe do a shared function where the logic of getting the user and service is shared