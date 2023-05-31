import os

from rest_framework import authentication, exceptions

from core.authentication.types import InternalToken, InternalUser

CODECOV_INTERNAL_TOKEN = os.environ.get("CODECOV_INTERNAL_TOKEN")


class InternalTokenAuthentication(authentication.TokenAuthentication):
    keyword = "Bearer"

    def authenticate_credentials(self, key):
        if key == CODECOV_INTERNAL_TOKEN:
            return (InternalUser(), InternalToken(token=key))

        raise exceptions.AuthenticationFailed("Invalid token.")
