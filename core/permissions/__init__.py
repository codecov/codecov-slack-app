from rest_framework.permissions import BasePermission

from core.permissions.mixins import InternalPermissionsMixin


class InternalTokenPermissions(BasePermission, InternalPermissionsMixin):
    def has_permission(self, request, view):
        return self.has_internal_token_permissions(request)
