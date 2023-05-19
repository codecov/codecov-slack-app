import os

from core.authentication.types import InternalToken, InternalUser

CODECOV_INTERNAL_TOKEN = os.environ.get("CODECOV_INTERNAL_TOKEN")


class InternalPermissionsMixin:
    def has_internal_token_permissions(self, request):
        if request.method != "POST":
            return False
        user = request.user
        auth = request.auth

        if not isinstance(request.user, InternalUser) or not isinstance(
            request.auth, InternalToken
        ):
            return False
        return (
            user.is_internal_user
            and auth.is_internal_token
            and auth.token == CODECOV_INTERNAL_TOKEN
        )
