from __future__ import annotations

import re
import typing as typ

import django.core.exceptions as dj_exc
import django.db.models as dj_models
import django.contrib.auth.models as dj_auth_models

from . import settings


# TODO categories


def _namespace_id_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value})


def _page_title_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value})


def _group_id_validator(value):
    if value in settings.GROUPS:
        raise dj_exc.ValidationError('invalid group ID', params={'value': value})


class Page(dj_models.Model):
    namespace_id = dj_models.IntegerField(validators=[_namespace_id_validator])
    title = dj_models.CharField(max_length=100, validators=[_page_title_validator])
    deleted = dj_models.BooleanField(default=False)
    protection_level = dj_models.CharField(max_length=100, validators=[_group_id_validator])

    def get_latest_revision(self) -> PageRevision:
        return PageRevision.objects.filter(page__namespace_id=self.namespace_id, page__title=self.title).latest('date')

    class Meta:
        unique_together = ('namespace_id', 'title')


class UserData(dj_models.Model):
    user = dj_models.OneToOneField(dj_auth_models.User, on_delete=dj_models.CASCADE)
    ip_address = dj_models.CharField(max_length=50, null=True, default=None)
    is_male = dj_models.BooleanField(null=True, default=None)
    skin = dj_models.CharField(max_length=50, default='default')

    @property
    def groups(self):
        return [settings.GROUPS[rel.group_id] for rel in self.user.usergrouprel_set.filter(user=self.user)]

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'UserData(user={self.user},ip_address={self.ip_address},is_male={self.is_male},skin={self.skin})'


class UserGroupRel(dj_models.Model):
    user = dj_models.ForeignKey(dj_auth_models.User, on_delete=dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[_group_id_validator])

    class Meta:
        unique_together = ('user', 'group_id')


class UserBlock(dj_models.Model):
    user = dj_models.ForeignKey(dj_auth_models.User, dj_models.CASCADE)
    page_or_namespace = dj_models.TextField()
    duration = dj_models.IntegerField()
    reason = dj_models.TextField(null=True, default=None)

    def get_page_title(self) -> typ.Optional[str]:
        if m := re.fullmatch('page:(.+)', self.page_or_namespace):
            return m.group(1)
        return None

    def get_namespace_id(self) -> typ.Optional[int]:
        if m := re.fullmatch(r'namespace:(\d+)', self.page_or_namespace):
            return int(m.group(1))
        return None


class User:
    """Simple wrapper class for Django users and associated user data."""

    def __init__(self, django_user: dj_auth_models.User, data: UserData):
        self.__django_user = django_user
        self.__data = data

    @property
    def django_user(self) -> dj_auth_models.User:
        return self.__django_user

    @property
    def data(self) -> UserData:
        return self.__data

    @property
    def username(self) -> str:
        return self.__django_user.username

    @property
    def groups(self):
        return self.__data.groups

    @property
    def is_anonymous(self) -> bool:
        return self.__data.ip_address is not None

    def has_right(self, right: str) -> bool:
        return any(map(lambda g: g.has_right(right), self.__data.groups))

    def has_right_on_page(self, right: str, namespace_id: int, title: str) -> bool:
        return any(map(lambda g: g.has_right_on_pages_in_namespace(right, namespace_id, title), self.__data.groups))

    def can_read_page(self, namespace_id: int, title: str):  # TODO prendre en compte les blocages
        return namespace_id in [6, 7] and re.fullmatch(fr'{self.username}(/.*)?', title) or \
               any(map(lambda g: g.can_read_pages_in_namespace(namespace_id), self.__data.groups))

    def can_edit_page(self, namespace_id: int, title: str):  # TODO prendre en compte les blocages
        return namespace_id in [6, 7] and re.fullmatch(fr'{self.username}(/.*)?', title) or \
               any(map(lambda g: g.can_edit_pages_in_namespace(namespace_id), self.__data.groups))

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'


class PageRevision(dj_models.Model):
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    author = dj_models.ForeignKey(dj_auth_models.User, dj_models.SET_NULL, null=True)
    date = dj_models.DateTimeField(auto_now_add=True)
    hidden = dj_models.BooleanField(default=False)
    content = dj_models.TextField()
    # minor = dj_models.BooleanField(default=False)  # TODO activer
    reverted_to = dj_models.IntegerField(null=True, default=None)

    def get_previous(self) -> typ.Optional[PageRevision]:
        return self.objects.filter(date__lt=self.date).latest('date')

    def get_reverted_revision(self) -> typ.Optional[PageRevision]:
        return self.objects.get(id=self.reverted_to) if self.reverted_to else None
