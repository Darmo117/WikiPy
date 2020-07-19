from __future__ import annotations

import django.core.exceptions as dj_exc
import django.db.models as dj_models

from . import api, settings


def _namespace_id_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value})


def _page_title_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value})


class Page(dj_models.Model):
    namespace_id = dj_models.IntegerField(validators=[_namespace_id_validator])
    title = dj_models.CharField(max_length=100, validators=[_page_title_validator], unique=True)
    deleted = dj_models.BooleanField(default=False)

    # TODO protection

    def get_full_title(self) -> str:
        return api.get_full_page_title(self.namespace_id, self.title)

    def get_latest_revision(self) -> PageRevision:
        return PageRevision.objects.filter(page__namespace_id=self.namespace_id, page__title=self.title).latest('date')


class User(dj_models.Model):
    name = dj_models.CharField(max_length=100, unique=True)
    ban_date = dj_models.DateTimeField(null=True)
    ban_duration = dj_models.IntegerField(null=True)  # In days
    ban_reason = dj_models.TextField(null=True)


def _user_action_validator(value):
    if value not in [UserJournalEntry.BANNED, UserJournalEntry.CHANGED_GROUP]:
        raise dj_exc.ValidationError('invalid user action ID', params={'value': value})


class UserJournalEntry(dj_models.Model):
    BANNED = 0
    CHANGED_GROUP = 1

    author = dj_models.ForeignKey(User, dj_models.SET_NULL, null=True)
    action = dj_models.IntegerField(validators=[_user_action_validator], editable=False)
    reason = dj_models.TextField(editable=False)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)


def _group_id_validator(value):
    if api.get_group_for_id(value) is None:
        raise dj_exc.ValidationError('invalid group ID', params={'value': value})


class UserGroupRel(dj_models.Model):
    user = dj_models.ForeignKey(User, dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[_group_id_validator], editable=False)
    # TODO empêcher un utilisateur d’être plusieurs plusieurs fois dans le même groupe.


class PageRevision(dj_models.Model):
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)
    author = dj_models.ForeignKey(User, dj_models.SET_NULL, null=True)
    hidden = dj_models.BooleanField(default=False)
    content = dj_models.TextField(editable=False)  # FIXME champ toujours éditable


def _action_validator(value):
    if value not in [PageActionsJournalEntry.DELETED, PageActionsJournalEntry.RENAMED, PageActionsJournalEntry.MOVED]:
        raise dj_exc.ValidationError('invalid action ID', params={'value': value})


class PageActionsJournalEntry(dj_models.Model):
    DELETED = 0
    RENAMED = 1
    MOVED = 2

    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    author = dj_models.ForeignKey(User, dj_models.SET_NULL, null=True)
    action = dj_models.IntegerField(validators=[_action_validator], editable=False)
    reason = dj_models.TextField(editable=False)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)
