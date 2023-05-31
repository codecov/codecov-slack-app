from django.contrib.auth.models import Group, Permission
from django.db.models.manager import EmptyManager


class DjangoUser(object):
    id = None
    pk = None
    is_staff = False
    is_superuser = False
    is_active = False
    _groups = EmptyManager(Group)
    _user_permissions = EmptyManager(Permission)

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return False

    @property
    def groups(self):
        return False

    @property
    def user_permissions(self):
        return False

    def get_user_permissions(self, obj=None):
        return False

    def get_group_permissions(self, obj=None):
        return False

    def get_all_permissions(self, obj=None):
        return False

    def has_perm(self, perm, obj=None):
        return False

    def has_perms(self, perm_list, obj=None):
        return False


class InternalUser(DjangoUser):
    is_internal_user = True

    pass


class DjangoToken(object):
    def __init__(self, token=None):
        self.token = token


class InternalToken(DjangoToken):
    is_internal_token = True

    pass
