from __future__ import annotations

import typing as typ

import django.core.exceptions as dj_exc
import django.db.models as dj_models

from . import api, settings


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

    def get_full_title(self) -> str:
        return api.get_full_page_title(self.namespace_id, self.title)

    def get_latest_revision(self) -> PageRevision:
        return PageRevision.objects.filter(page__namespace_id=self.namespace_id, page__title=self.title).latest('date')

    class Meta:
        unique_together = ('namespace_id', 'title')


class User(dj_models.Model):
    name = dj_models.CharField(max_length=100, unique=True)
    is_male = dj_models.BooleanField(null=True)
    ban_date = dj_models.DateTimeField(null=True)
    ban_duration = dj_models.IntegerField(null=True)  # In days
    ban_reason = dj_models.TextField(null=True)

    @property
    def groups(self):
        return [settings.GROUPS[rel.group_id] for rel in self.usergrouprel_set.filter(user=self)]

    def is_logged_in(self) -> bool:
        return settings.GROUPS[settings.GROUP_USERS] in self.groups

    def has_right(self, right: str) -> bool:
        return any(map(lambda g: g.has_right(right), self.groups))

    def has_right_on_page(self, right: str, page) -> bool:
        return any(map(lambda g: g.has_right_on_page(right, page), self.groups))

    def can_read_page(self, page: Page):
        return any(map(lambda g: g.can_edit_page(page), self.groups))

    def can_edit_page(self, page: Page):
        return any(map(lambda g: g.can_edit_page(page), self.groups))


class UserGroupRel(dj_models.Model):
    user = dj_models.ForeignKey(User, dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[_group_id_validator])

    class Meta:
        unique_together = ('user', 'group_id')


class PageRevision(dj_models.Model):
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    author = dj_models.ForeignKey(User, dj_models.SET_NULL, null=True)
    date = dj_models.DateTimeField(auto_now_add=True)
    hidden = dj_models.BooleanField(default=False)
    content = dj_models.TextField()
    reverted_to = dj_models.IntegerField(null=True)

    def get_previous(self) -> typ.Optional[PageRevision]:
        return self.objects.filter(date__lt=self.date).latest('date')

    def get_reverted_revision(self) -> typ.Optional[PageRevision]:
        return self.objects.get(id=self.reverted_to) if self.reverted_to else None
