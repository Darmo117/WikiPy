from __future__ import annotations

import django.db.models as dj_models
import django.core.exceptions as dj_exc

from . import api


####################
# Database classes #
####################


class Page(dj_models.Model):
    namespace_id = dj_models.IntegerField()
    title = dj_models.CharField(max_length=100, unique=True)
    deleted = dj_models.BooleanField()

    # TODO protection

    def get_full_title(self) -> str:
        return api.get_full_page_title(self.namespace_id, self.title)

    def get_lastest_revision(self) -> PageRevision:
        return PageRevision.objects.get(page=self).latest('date')


class User(dj_models.Model):
    name = dj_models.CharField(max_length=100, unique=True)
    ban_date = dj_models.DateTimeField()
    ban_duration = dj_models.IntegerField()  # In days
    ban_reason = dj_models.TextField()


def _user_action_validator(value):
    if value not in [UserJournalEntry.BANNED, UserJournalEntry.CHANGED_GROUP]:
        raise dj_exc.ValidationError('invalid user action ID', params={'value': value})


class UserJournalEntry(dj_models.Model):
    BANNED = 0
    CHANGED_GROUP = 1

    author = dj_models.ForeignKey(User, dj_models.SET_NULL)
    action = dj_models.IntegerField(validators=[_user_action_validator], editable=False)
    reason = dj_models.TextField(editable=False)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)


def _group_id_validator(value):
    if api.get_group_for_id(value) is None:
        raise dj_exc.ValidationError('invalid group ID', params={'value': value})


class UserGroupRel(dj_models.Model):
    user = dj_models.ForeignKey(User, dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[_group_id_validator], editable=False)


class PageRevision(dj_models.Model):
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)
    author = dj_models.ForeignKey(User, dj_models.SET_NULL)
    hidden = dj_models.BooleanField()
    content = dj_models.TextField(editable=False)


def _action_validator(value):
    if value not in [PageActionsJournalEntry.DELETED, PageActionsJournalEntry.RENAMED, PageActionsJournalEntry.MOVED]:
        raise dj_exc.ValidationError('invalid action ID', params={'value': value})


class PageActionsJournalEntry(dj_models.Model):
    DELETED = 0
    RENAMED = 1
    MOVED = 2

    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    author = dj_models.ForeignKey(User, dj_models.SET_NULL)
    action = dj_models.IntegerField(validators=[_action_validator], editable=False)
    reason = dj_models.TextField(editable=False)
    date = dj_models.DateTimeField(auto_now_add=True, editable=False)

#################
# Other classes #
#################
