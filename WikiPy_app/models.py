from __future__ import annotations

import re
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.core.exceptions as dj_exc
import django.db.models as dj_models

from . import settings


# TODO categories


def _namespace_id_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value}, code='invalid')


def _page_title_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value}, code='invalid')


def _group_id_validator(value):
    if value not in settings.GROUPS:
        raise dj_exc.ValidationError('invalid group ID', params={'value': value}, code='invalid')


def _content_model_validator(value):
    if value not in settings.PAGE_TYPES:
        raise dj_exc.ValidationError('invalid content model', params={'value': value}, code='invalid')


def _language_validator(value):
    if not settings.i18n.get_language(value):
        raise dj_exc.ValidationError('invalid content model', params={'value': value}, code='invalid')


def _non_validator(_):
    pass


# Cannot inherit Django’s Model class as it causes problems with foreign keys.
class LockableModel:
    __locked: bool = False

    def lock(self):
        self.__locked = True

    def save(self, *args, **kwargs):
        if self.__locked:
            raise RuntimeError('object is locked')
        else:
            # All subclasses should also inherit Django’s Model class, so save() method should be defined.
            # noinspection PyUnresolvedReferences
            super().save(*args, **kwargs)


# Disable default username validator
# Validation is handled by API
class CustomUser(dj_auth_models.AbstractUser, LockableModel):
    username_validator = _non_validator


class Page(LockableModel, dj_models.Model):
    namespace_id = dj_models.IntegerField(validators=[_namespace_id_validator])
    title = dj_models.CharField(max_length=100, validators=[_page_title_validator])
    deleted = dj_models.BooleanField(default=False)
    protection_level = dj_models.CharField(max_length=100, validators=[_group_id_validator])
    content_model = dj_models.CharField(max_length=20, default=settings.PAGE_TYPE_WIKI,
                                        validators=[_content_model_validator])
    content_language_code = dj_models.CharField(max_length=20, default=settings.DEFAULT_LANGUAGE_CODE,
                                                validators=[_language_validator])

    @property
    def content_language(self) -> settings.i18n.Language:
        return settings.i18n.get_language(self.content_language_code)

    @property
    def url_title(self) -> str:
        from . import api
        return api.as_url_title(self.title, escape=True)

    @property
    def full_title(self) -> str:
        from . import api
        return api.get_full_page_title(self.namespace_id, self.title)

    @property
    def url_full_title(self) -> str:
        from . import api
        return api.as_url_title(self.full_title, escape=True)

    @property
    def namespace(self) -> settings.Namespace:
        return settings.NAMESPACES[self.namespace_id]

    @property
    def latest_revision(self) -> typ.Optional[PageRevision]:
        try:
            return PageRevision.objects.filter(page=self).latest('date')
        except PageRevision.DoesNotExist:
            return None

    def get_revision(self, revision_id: int) -> typ.Optional[PageRevision]:
        try:
            return PageRevision.objects.filter(page=self).get(id=revision_id)
        except PageRevision.DoesNotExist:
            return None

    class Meta:
        unique_together = ('namespace_id', 'title')


class PageRevision(LockableModel, dj_models.Model):
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.SET_NULL, null=True)
    date = dj_models.DateTimeField(auto_now_add=True)
    text_hidden = dj_models.BooleanField(default=False)
    author_hidden = dj_models.BooleanField(default=False)
    comment_hidden = dj_models.BooleanField(default=False)
    content = dj_models.TextField()
    comment = dj_models.CharField(max_length=200, null=True, default=None)
    minor = dj_models.BooleanField(default=False)
    diff_size = dj_models.IntegerField()
    reverted_to = dj_models.IntegerField(null=True, default=None)

    def get_previous(self, ignore_hidden: bool = True) -> typ.Optional[PageRevision]:
        try:
            params = {
                'page': self.page,
                'date__lt': self.date,
            }
            if ignore_hidden:
                params['text_hidden'] = False
            return PageRevision.objects.filter(**params).latest('date')
        except PageRevision.DoesNotExist:
            return None

    def get_next(self, ignore_hidden: bool = True) -> typ.Optional[PageRevision]:
        try:
            params = {
                'page': self.page,
                'date__gt': self.date,
            }
            if ignore_hidden:
                params['text_hidden'] = False
            return PageRevision.objects.filter(**params).earliest('date')
        except PageRevision.DoesNotExist:
            return None

    def get_reverted_revision(self) -> typ.Optional[PageRevision]:
        return PageRevision.objects.get(id=self.reverted_to) if self.reverted_to else None

    @property
    def size(self) -> int:
        return len(self.content.encode('utf-8'))

    @property
    def has_created_page(self) -> bool:
        return self.get_previous(ignore_hidden=False) is None

    @property
    def is_bot_edit(self) -> bool:
        return UserData.objects.get(user=self.author).is_in_group(settings.GROUP_BOTS)


class UserData(LockableModel, dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    ip_address = dj_models.CharField(max_length=50, null=True, default=None)
    is_male = dj_models.BooleanField(null=True, default=None)
    skin = dj_models.CharField(max_length=50, default='default')
    lang_code = dj_models.CharField(max_length=10, default=settings.DEFAULT_LANGUAGE_CODE)
    timezone = dj_models.CharField(max_length=50)
    datetime_format_id = dj_models.IntegerField()
    signature = dj_models.CharField(max_length=100)

    @property
    def groups(self):
        # noinspection PyUnresolvedReferences
        return [settings.GROUPS[rel.group_id] for rel in self.user.usergrouprel_set.filter(user=self.user)]

    @property
    def group_ids(self):
        # noinspection PyUnresolvedReferences
        return [rel.group_id for rel in self.user.usergrouprel_set.filter(user=self.user)]

    def is_in_group(self, group_id: str) -> bool:
        group = settings.GROUPS.get(group_id)
        return group is not None and group in self.groups

    @property
    def prefered_language(self) -> settings.i18n.Language:
        return settings.i18n.get_language(self.lang_code)

    @property
    def datetime_format(self):
        formats = self.prefered_language.datetime_formats
        return formats[self.datetime_format_id % len(formats)]

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'UserData(user={self.user},ip_address={self.ip_address},is_male={self.is_male},skin={self.skin})'


class UserGroupRel(LockableModel, dj_models.Model):
    user = dj_models.ForeignKey(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[_group_id_validator])

    class Meta:
        unique_together = ('user', 'group_id')


class UserBlock(LockableModel, dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), dj_models.CASCADE)
    on_whole_site = dj_models.BooleanField()
    pages = dj_models.TextField()
    namespaces = dj_models.TextField()
    on_own_talk_page = dj_models.BooleanField()
    duration = dj_models.IntegerField()
    reason = dj_models.TextField(null=True, default=None)

    def get_page_titles(self) -> typ.Iterable[str]:
        return self.pages.split(',')

    def get_namespace_ids(self) -> typ.Iterable[int]:
        return map(int, self.namespaces.split(','))


class User:
    """Simple wrapper class for Django users and associated user data."""

    def __init__(self, django_user: CustomUser, data: UserData):
        self.__django_user = django_user
        self.__django_user.lock()
        self.__data = data
        self.__data.lock()

    @property
    def django_user(self) -> dj_auth_models.AbstractUser:
        return self.__django_user

    @property
    def data(self) -> UserData:
        return self.__data

    @property
    def username(self) -> str:
        return self.__django_user.username

    @property
    def prefered_language(self) -> settings.i18n.Language:
        if self.__data:
            return self.__data.prefered_language
        else:
            return settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE)

    @property
    def datetime_format(self):
        return self.data.datetime_format

    @property
    def groups(self) -> typ.List[settings.UserGroup]:
        return self.__data.groups

    @property
    def group_ids(self) -> typ.List[str]:
        return self.__data.group_ids

    @property
    def is_bot(self) -> bool:
        return self.is_in_group(settings.GROUP_BOTS)

    @property
    def is_anonymous(self) -> bool:
        return self.__data.ip_address is not None

    @property
    def is_logged_in(self) -> bool:
        return self.__django_user.is_authenticated and not self.is_anonymous

    def is_in_group(self, group_id: str) -> bool:
        return self.__data.is_in_group(group_id)

    def has_right(self, right: str) -> bool:
        return any(map(lambda g: g.has_right(right), self.__data.groups))

    def has_right_on_page(self, right: str, namespace_id: int, title: str) -> bool:
        return any(map(lambda g: g.has_right_on_pages_in_namespace(right, namespace_id, title), self.__data.groups))

    def can_read_page(self, namespace_id: int, title: str) -> bool:  # TODO prendre en compte les blocages
        return (namespace_id in [settings.USER_NS.id, settings.USER_NS_TALK.id] and
                re.fullmatch(fr'{self.username}(/.*)?', title) or
                self.has_right(settings.RIGHT_EDIT_USER_PAGES) or
                any(map(lambda g: g.can_read_pages_in_namespace(namespace_id), self.__data.groups)))

    def can_edit_page(self, namespace_id: int, title: str) -> bool:  # TODO prendre en compte les blocages
        return (namespace_id in [settings.USER_NS.id, settings.USER_NS_TALK.id] and
                re.fullmatch(fr'{self.username}(/.*)?', title) or
                self.has_right(settings.RIGHT_EDIT_USER_PAGES) or
                any(map(lambda g: g.can_edit_pages_in_namespace(namespace_id), self.__data.groups)))

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'
