import requests
from rest_framework.exceptions import ValidationError


def validate_gh_call_params(code, state):
    if not code:
        raise ValidationError("Missing code parameter")
    if not state:
        raise ValidationError("Missing state parameter")


def get_github_user(access_token):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("id"), data.get("login")
    else:
        return None, None
