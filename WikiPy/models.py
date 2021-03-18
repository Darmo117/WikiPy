from __future__ import annotations

import dataclasses
import datetime
import re
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_auth_models
import django.core.exceptions as dj_exc
import django.core.validators as dj_valid
import django.db.models as dj_models
import pytz

from . import settings


def username_validator(value: str, anonymous: bool = False):
    _username_validator2(value)
    if not anonymous and value.startswith('Anonymous-'):
        raise dj_exc.ValidationError('invalid username', code='invalid')


def _username_validator2(value: str):
    if '/' in value or settings.INVALID_TITLE_REGEX.search(value):
        raise dj_exc.ValidationError('invalid username', code='invalid')


def password_validator(value: str):
    if value is None or value.strip() == '':
        raise dj_exc.ValidationError('invalid password', code='invalid')


def email_validator(value):
    dj_valid.EmailValidator()(value)


def namespace_id_validator(value):
    if value not in settings.NAMESPACES:
        raise dj_exc.ValidationError('invalid namespace ID', params={'value': value}, code='invalid')


def page_title_validator(value):
    if settings.INVALID_TITLE_REGEX.search(value):
        raise dj_exc.ValidationError('invalid page title', params={'value': value}, code='invalid')


def group_id_validator(value):
    if value not in settings.GROUPS:
        raise dj_exc.ValidationError('invalid group ID', params={'value': value}, code='invalid')


def content_model_validator(value):
    if value not in settings.PAGE_TYPES:
        raise dj_exc.ValidationError('invalid content model', params={'value': value}, code='invalid')


def language_validator(value):
    if not settings.i18n.get_language(value):
        raise dj_exc.ValidationError('invalid language', params={'value': value}, code='invalid')


def expiration_date_validator(value: datetime.date):
    if value <= datetime.datetime.now().date():
        raise dj_exc.ValidationError('invalid expiration date', params={'value': value}, code='invalid')


def _non_validator(_):
    pass


def _default_revisions_list_size_validator(value):
    if not (settings.REVISIONS_LIST_PAGE_MIN <= value <= settings.REVISIONS_LIST_PAGE_MAX):
        raise dj_exc.ValidationError('invalid revisions list page size', code='invalid', params={'value': value})


def _rc_max_days_validator(value):
    if not (settings.RC_DAYS_MIN <= value <= settings.RC_DAYS_MAX):
        raise dj_exc.ValidationError('invalid recent changes days limit', code='invalid', params={'value': value})


def _rc_max_revisions_validator(value):
    if not (settings.RC_REVISIONS_MIN <= value <= settings.RC_REVISIONS_MAX):
        raise dj_exc.ValidationError('invalid recent changes revisions limit', code='invalid', params={'value': value})


# Cannot inherit Django’s Model class as it causes problems with foreign keys.
class LockableModel:
    __locked: bool = False

    def lock(self) -> LockableModel:
        self.__locked = True
        return self  # Enable chaining

    # noinspection PyUnresolvedReferences
    def save(self, *args, **kwargs):
        if self.__locked:
            raise RuntimeError('object is locked')
        else:
            # All subclasses should also inherit Django’s Model class,
            # so save() and full_clean() methods should be defined.
            self.full_clean()
            super().save(*args, **kwargs)


# Disable default username validator
# Validation is handled by API
class CustomUser(dj_auth_models.AbstractUser, LockableModel):
    username_validator = username_validator


class Page(LockableModel, dj_models.Model):
    namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    deleted = dj_models.BooleanField(default=False)
    content_model = dj_models.CharField(max_length=20, default=settings.PAGE_TYPE_WIKI,
                                        validators=[content_model_validator])
    content_language_code = dj_models.CharField(max_length=20, default=settings.DEFAULT_LANGUAGE_CODE,
                                                validators=[language_validator])

    @property
    def exists(self) -> bool:
        return self.id is not None and not self.deleted

    @property
    def content_language(self) -> settings.i18n.Language:
        return settings.i18n.get_language(self.content_language_code)

    @property
    def url_title(self) -> str:
        from .api import titles as api_titles
        return api_titles.as_url_title(self.title, escape=True)

    @property
    def full_title(self) -> str:
        from .api import titles as api_titles
        return api_titles.get_full_page_title(self.namespace_id, self.title)

    @property
    def url_full_title(self) -> str:
        from .api import titles as api_titles
        return api_titles.as_url_title(self.full_title, escape=True)

    @property
    def namespace(self) -> settings.Namespace:
        return settings.NAMESPACES[self.namespace_id]

    @property
    def subpage_title(self) -> typ.Tuple[typ.Optional[str], str]:
        ns = settings.NAMESPACES.get(self.namespace_id)
        if ns and ns.allows_subpages and '/' in self.title:
            # noinspection PyTypeChecker
            return tuple(self.title.rsplit('/', maxsplit=1))
        return None, self.title

    @property
    def is_category(self) -> bool:
        return self.namespace_id == settings.CATEGORY_NS.id

    @property
    def is_category_hidden(self) -> bool:
        return self.is_category and CategoryData.objects.get(page=self).maintenance

    @property
    def latest_revision(self) -> typ.Optional[PageRevision]:
        """
        Returns the latest non-hidden revision for this page.

        :return: The latest non-hidden revision.
        """
        try:
            return PageRevision.objects.filter(page=self, hidden=False).latest('date')
        except PageRevision.DoesNotExist:
            return None

    def get_revision(self, revision_id: int) -> typ.Optional[PageRevision]:
        try:
            return PageRevision.objects.filter(page=self).get(id=revision_id)
        except PageRevision.DoesNotExist:
            return None

    def get_categories(self) -> typ.Iterable[str]:
        return list(map(lambda pc: pc.category_name, PageCategory.objects.filter(page=self).order_by('category_name')))

    class Meta:
        unique_together = ('namespace_id', 'title')


class CategoryData(LockableModel, dj_models.Model):
    page = dj_models.OneToOneField(Page, dj_models.CASCADE)
    maintenance = dj_models.BooleanField(default=False)


class PageCategory(LockableModel, dj_models.Model):
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE)
    # Do not link to Category object as pages might be associated to non-existant categories
    category_name = dj_models.CharField(max_length=Page._meta.get_field('title').max_length,
                                        validators=[page_title_validator])
    sort_key = dj_models.CharField(max_length=100, blank=True, null=True, default=None)

    class Meta:
        unique_together = ('page', 'category_name')


class Revision(LockableModel, dj_models.Model):
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE)
    date = dj_models.DateTimeField(auto_now_add=True)
    hidden = dj_models.BooleanField(default=False)
    author_hidden = dj_models.BooleanField(default=False)
    comment_hidden = dj_models.BooleanField(default=False)
    content = dj_models.TextField(blank=True)
    comment = dj_models.CharField(max_length=200, blank=True, null=True, default=None)
    minor = dj_models.BooleanField(default=False)
    diff_size = dj_models.IntegerField()
    reverted_to = dj_models.IntegerField(blank=True, null=True, default=None)

    class Meta:
        abstract = True

    @property
    def object_name(self) -> str:
        raise NotImplementedError('object_name')

    @property
    def _actual_class(self):
        return self.__class__

    @property
    def _object(self):
        return getattr(self, self.object_name)

    def get_previous(self, ignore_hidden: bool = True) -> typ.Optional[Revision]:
        try:
            params = {
                self.object_name: self._object,
                'date__lt': self.date,
            }
            if ignore_hidden:
                params['hidden'] = False
            return self._actual_class.objects.filter(**params).latest('date')
        except self._actual_class.DoesNotExist:
            return None

    def get_next(self, ignore_hidden: bool = True) -> typ.Optional[Revision]:
        try:
            params = {
                self.object_name: self._object,
                'date__gt': self.date,
            }
            if ignore_hidden:
                params['hidden'] = False
            return self._actual_class.objects.filter(**params).earliest('date')
        except self._actual_class.DoesNotExist:
            return None

    def get_reverted_revision(self) -> typ.Optional[Revision]:
        # FIXME revision reverted_to might be hidden
        return self._actual_class.objects.get(id=self.reverted_to) if self.reverted_to else None

    @property
    def size(self) -> int:
        return len(self.content.encode('utf-8'))

    @property
    def is_bot_edit(self) -> bool:
        return UserData.objects.get(user=self.author).is_in_group(settings.GROUP_BOTS)


class PageRevision(Revision):
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE)

    @property
    def object_name(self) -> str:
        return 'page'

    @property
    def has_created_page(self) -> bool:
        return self.get_previous(ignore_hidden=False) is None


class PageProtectionStatus(LockableModel, dj_models.Model):
    # Do not link to Page object as non-existant pages might be protected
    page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    protection_level = dj_models.CharField(max_length=100, validators=[group_id_validator])
    reason = dj_models.CharField(max_length=200)
    expiration_date = dj_models.DateField(blank=True, null=True, validators=[expiration_date_validator])

    class Meta:
        unique_together = ('page_namespace_id', 'page_title')


class TalkTopic(LockableModel, dj_models.Model):
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE)
    page = dj_models.ForeignKey(Page, dj_models.CASCADE)
    title = dj_models.CharField(max_length=150)
    date = dj_models.DateTimeField(auto_now_add=True)
    pinned = dj_models.BooleanField(default=False)
    deleted = dj_models.BooleanField(default=False)

    @property
    def post_date(self) -> datetime.datetime:
        return self.message_set.earliest('post_date').date

    @property
    def last_updated(self) -> datetime.datetime:
        return self.message_set.latest('last_updated').date


class Message(LockableModel, dj_models.Model):
    topic = dj_models.ForeignKey(TalkTopic, dj_models.CASCADE)
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE)
    replied_to = dj_models.ForeignKey('self', dj_models.SET_NULL, null=True)
    deleted = dj_models.BooleanField(default=False)

    @property
    def post_date(self) -> datetime.datetime:
        return self.messagerevision_set.earliest('date').date

    @property
    def last_updated(self) -> datetime.datetime:
        return self.messagerevision_set.latest('date').date


class MessageRevision(Revision):
    message = dj_models.ForeignKey(Message, on_delete=dj_models.CASCADE)

    @property
    def object_name(self) -> str:
        return 'message'


@dataclasses.dataclass(frozen=True)
class Gender:
    code: str
    i18n_code: str


NEUTRAL_GENDER = Gender(code='neutral', i18n_code='neutral')
FEMALE_GENDER = Gender(code='female', i18n_code='feminine')
MALE_GENDER = Gender(code='male', i18n_code='masculine')
GENDERS = {gender.code: gender for gender in (NEUTRAL_GENDER, FEMALE_GENDER, MALE_GENDER)}


# TODO make data accessible from JS API (read-only)?
class UserData(LockableModel, dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    ip_address = dj_models.CharField(max_length=50, blank=True, null=True, default=None)

    # True = female, False = Male, None = Undefined
    _gender = dj_models.BooleanField(blank=True, null=True, default=None)
    lang_code = dj_models.CharField(max_length=10, default=settings.DEFAULT_LANGUAGE_CODE)
    signature = dj_models.CharField(max_length=100)
    email_confirmation_date = dj_models.DateTimeField(blank=True, null=True, default=None)
    email_confirmation_code = dj_models.CharField(max_length=50, blank=True, null=True, default=None)
    email_pending_confirmation = dj_models.CharField(max_length=100, blank=True, null=True, default=None)
    users_can_send_emails = dj_models.BooleanField(default=True)
    send_copy_of_sent_emails = dj_models.BooleanField(default=False)
    send_watchlist_emails = dj_models.BooleanField(default=False)
    send_minor_watchlist_emails = dj_models.BooleanField(default=False)

    skin = dj_models.CharField(max_length=50, default='default')
    timezone = dj_models.CharField(max_length=50)
    datetime_format_id = dj_models.IntegerField(blank=True, null=True, default=None)
    max_image_file_preview_size = dj_models.IntegerField()  # Pixels
    max_image_thumbnail_size = dj_models.IntegerField()  # Pixels
    enable_media_viewer = dj_models.BooleanField(default=True)
    display_maintenance_categories = dj_models.BooleanField(default=False)
    numbered_section_titles = dj_models.BooleanField(default=False)
    default_revisions_list_size = dj_models.IntegerField(default=50,
                                                         validators=[_default_revisions_list_size_validator])
    confirm_rollback = dj_models.BooleanField(default=False)

    all_edits_minor = dj_models.BooleanField(default=False)
    blank_comment_prompt = dj_models.BooleanField(default=False)
    unsaved_changes_warning = dj_models.BooleanField(default=True)
    show_preview_first_edit = dj_models.BooleanField(default=False)
    preview_above_edit_box = dj_models.BooleanField(default=True)

    rc_max_days = dj_models.IntegerField(default=2, validators=[_rc_max_days_validator])
    rc_max_revisions = dj_models.IntegerField(default=50, validators=[_rc_max_revisions_validator])
    rc_group_by_page = dj_models.BooleanField(default=False)
    rc_hide_minor = dj_models.BooleanField(default=False)
    rc_hide_categories = dj_models.BooleanField(default=False)
    rc_hide_patrolled = dj_models.BooleanField(default=False)
    rc_hide_patrolled_new_pages = dj_models.BooleanField(default=False)

    @property
    def is_female(self) -> bool:
        return self.gender == FEMALE_GENDER

    @property
    def is_male(self) -> bool:
        return self.gender == MALE_GENDER

    @property
    def is_genderless(self) -> bool:
        return self.gender == NEUTRAL_GENDER

    @property
    def gender(self) -> Gender:
        if self._gender:
            return FEMALE_GENDER
        elif self._gender is not None:
            return MALE_GENDER
        return NEUTRAL_GENDER

    @gender.setter
    def gender(self, value: Gender):
        self._gender = {
            FEMALE_GENDER: True,
            MALE_GENDER: False,
            NEUTRAL_GENDER: None,
        }.get(value)

    @property
    def email_confirmed(self) -> bool:
        return self.email_confirmation_date is not None

    @property
    def groups(self) -> typ.List[settings.UserGroup]:
        # noinspection PyUnresolvedReferences
        return [settings.GROUPS[rel.group_id] for rel in self.user.usergrouprel_set.filter(user=self.user)]

    @property
    def group_ids(self) -> typ.List[str]:
        # noinspection PyUnresolvedReferences
        return [rel.group_id for rel in self.user.usergrouprel_set.filter(user=self.user)]

    def is_in_group(self, group_id: str) -> bool:
        group = settings.GROUPS.get(group_id)
        return group is not None and group in self.groups

    @property
    def prefered_language(self) -> settings.i18n.Language:
        return settings.i18n.get_language(self.lang_code)

    def get_datetime_format(self, language: settings.i18n.Language = None) -> str:
        formats = language.datetime_formats if language else self.prefered_language.datetime_formats
        if self.datetime_format_id is not None:
            format_id = self.datetime_format_id
        else:
            format_id = language.default_datetime_format_id
        return formats[format_id % len(formats)]

    @property
    def timezone_info(self) -> datetime.tzinfo:
        return pytz.timezone(self.timezone)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'UserData(user={self.user},ip_address={self.ip_address},gender={self._gender},skin={self.skin})'


class UserGroupRel(LockableModel, dj_models.Model):
    user = dj_models.ForeignKey(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[group_id_validator])

    class Meta:
        unique_together = ('user', 'group_id')


class UserBlock(LockableModel, dj_models.Model):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), dj_models.CASCADE)
    on_whole_site = dj_models.BooleanField()
    pages = dj_models.TextField()
    namespaces = dj_models.TextField()
    on_own_talk_page = dj_models.BooleanField()
    duration = dj_models.IntegerField()
    reason = dj_models.TextField(blank=True, null=True, default=None)

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

    def get_datetime_format(self, language: settings.i18n.Language = None) -> str:
        return self.data.get_datetime_format(language)

    def is_in_group(self, group_id: str) -> bool:
        return self.__data.is_in_group(group_id)

    def has_right(self, right: str) -> bool:
        return any(map(lambda g: g.has_right(right), self.__data.groups))

    def has_right_on_namespace(self, right: str, namespace_id: int) -> bool:
        return any(map(lambda g: g.has_right_on_pages_in_namespace(right, namespace_id), self.__data.groups))

    def can_read_page(self, namespace_id: int, title: str) -> bool:  # TODO prendre en compte les blocages
        return (namespace_id == settings.USER_NS.id and re.fullmatch(fr'{self.username}(/.*)?', title)
                or self.has_right(settings.RIGHT_EDIT_USER_PAGES)
                or any(map(lambda g: g.can_read_pages_in_namespace(namespace_id), self.__data.groups)))

    # TODO prendre en compte les blocages
    def can_edit_page(self, namespace_id: int, title: str) -> bool:
        try:
            page_protection = PageProtectionStatus.objects.get(page_namespace_id=namespace_id, page_title=title)
        except PageProtectionStatus.DoesNotExist:
            page_protection = None

        return ((not page_protection or self.is_in_group(page_protection.protection_level))
                and ((namespace_id == settings.USER_NS.id and re.fullmatch(fr'{self.username}(/.*)?', title))
                     or self.has_right(settings.RIGHT_EDIT_USER_PAGES)
                     or any(map(lambda g: g.can_edit_pages_in_namespace(namespace_id), self.__data.groups))))

    def can_rename_page(self, namespace_id: int, title: str) -> bool:
        from .api import pages as api_pages

        return (self.has_right(settings.RIGHT_RENAME_PAGES)
                and api_pages.page_exists(namespace_id, title)
                and self.can_edit_page(namespace_id, title))

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'


########
# Logs #
########


class LogEntry(LockableModel, dj_models.Model):
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE, blank=True, null=True)
    date = dj_models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def format_key(self) -> str:
        return ''

    @classmethod
    def search(cls, performer: str = None, from_date: datetime.date = None, to_date: datetime.date = None, **kwargs) \
            -> typ.Sequence[LogEntry]:
        args = {**kwargs}
        if performer:
            args['author__username'] = performer
        if from_date:
            args['date__gte'] = from_date
        if to_date:
            args['date_lte'] = to_date
        return cls.objects.filter(**args).order_by('-date')


#############
# User Logs #
#############


class UserLogEntry(LogEntry):
    target_user = dj_models.CharField(max_length=150, validators=[_username_validator2])
    reason = dj_models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        abstract = True

    @classmethod
    def search(cls, performer=None, from_date=None, to_date=None, **kwargs):
        from .api import titles as api_titles
        args = {}
        if full_title := kwargs.get('page_title_or_username'):
            ns_id, title = api_titles.extract_namespace_and_title(full_title, ns_as_id=True)
            args['target_user'] = title if ns_id == settings.USER_NS.id else full_title
        return super().search(performer, from_date, to_date, **args)


class UserCreationLogEntry(LogEntry):
    automatic = dj_models.BooleanField()

    @property
    def format_key(self) -> str:
        return f'log.{LOG_USER_CREATION}.entry' + ('_automatic' if self.automatic else '')

    @classmethod
    def search(cls, performer=None, from_date=None, to_date=None, **kwargs):
        return super().search(performer, from_date, to_date)


class UserRenamingLogEntry(UserLogEntry):
    subject_new_username = dj_models.CharField(max_length=150)


class UserBlockLogEntry(UserLogEntry):
    expiration_date = dj_models.DateField(blank=True, null=True)
    # TODO add pages/namespaces


class UserGroupChangeLogEntry(UserLogEntry):
    group = dj_models.CharField(max_length=20, validators=[group_id_validator])
    joined = dj_models.BooleanField()
    expiration_date = dj_models.DateField(blank=True, null=True)

    @property
    def format_key(self) -> str:
        key = f'log.{LOG_USER_GROUP_CHANGE}.entry' + ('' if self.author else '_automatic') + '.'
        if self.joined:
            key += 'added'
            if self.expiration_date:
                key += '_until'
        else:
            key += 'removed'
        return key


#############
# Page Logs #
#############


class PageLogEntry(LogEntry):
    # Do not link to Page object as non-existant/deleted pages might be concerned
    page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    reason = dj_models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def full_page_title(self):
        from .api import titles as api_titles
        return api_titles.get_full_page_title(self.page_namespace_id, self.page_title)

    @classmethod
    def search(cls, performer=None, from_date=None, to_date=None, **kwargs):
        from .api import titles as api_titles
        args = {}
        if title := kwargs.get('page_title_or_username'):
            ns_id, title = api_titles.extract_namespace_and_title(title, ns_as_id=True)
            args['page_namespace_id'] = ns_id
            args['page_title'] = title
        return super().search(performer, from_date, to_date, **args)


class PageProtectionLogEntry(PageLogEntry):
    protection_level = dj_models.CharField(max_length=100, validators=[group_id_validator])
    expiration_date = dj_models.DateField(blank=True, null=True)

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_PROTECTION}.entry' + ('' if self.expiration_date else '_no_date')


class PageRenamingLogEntry(PageLogEntry):
    new_page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    new_page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    created_redirection = dj_models.BooleanField()

    @property
    def new_full_page_title(self) -> str:
        from .api import titles as api_titles
        return api_titles.get_full_page_title(self.new_page_namespace_id, self.new_page_title)

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_RENAME}.entry' + ('_redirect' if self.created_redirection else '')


class PageDeletionLogEntry(PageLogEntry):
    deleted = dj_models.BooleanField()

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_DELETION}.entry' + ('_deleted' if self.deleted else '_restored')


class PageCreationLogEntry(PageLogEntry):
    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_CREATION}.entry'


def register_journals(registry):
    registry.register_log(LOG_USER_CREATION, UserCreationLogEntry)
    registry.register_log(LOG_USER_RENAME, UserRenamingLogEntry)
    registry.register_log(LOG_USER_BLOCK, UserBlockLogEntry)
    registry.register_log(LOG_USER_GROUP_CHANGE, UserGroupChangeLogEntry)
    registry.register_log(LOG_PAGE_PROTECTION, PageProtectionLogEntry)
    registry.register_log(LOG_PAGE_CREATION, PageCreationLogEntry)
    registry.register_log(LOG_PAGE_DELETION, PageDeletionLogEntry)
    registry.register_log(LOG_PAGE_RENAME, PageRenamingLogEntry)


LOG_USER_CREATION = 'user_creation'
LOG_USER_RENAME = 'user_rename'
LOG_USER_BLOCK = 'user_block'
LOG_USER_GROUP_CHANGE = 'user_group_change'
LOG_PAGE_PROTECTION = 'page_protection'
LOG_PAGE_CREATION = 'page_creation'
LOG_PAGE_DELETION = 'page_deletion'
LOG_PAGE_RENAME = 'page_rename'
