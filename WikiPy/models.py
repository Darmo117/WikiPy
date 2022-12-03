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
    if value is None:
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


def _default_revisions_list_size_validator(value):
    if not (settings.REVISIONS_LIST_PAGE_MIN <= value <= settings.REVISIONS_LIST_PAGE_MAX):
        raise dj_exc.ValidationError('invalid revisions list page size', code='invalid', params={'value': value})


def _rc_max_days_validator(value):
    if not (settings.RC_DAYS_MIN <= value <= settings.RC_DAYS_MAX):
        raise dj_exc.ValidationError('invalid recent changes days limit', code='invalid', params={'value': value})


def _rc_max_revisions_validator(value):
    if not (settings.RC_REVISIONS_MIN <= value <= settings.RC_REVISIONS_MAX):
        raise dj_exc.ValidationError('invalid recent changes revisions limit', code='invalid', params={'value': value})


class LockableModel(dj_models.Model):
    _locked: bool = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for attr_name in dir(cls):
            try:
                attr = getattr(cls, attr_name)
            except (ValueError, AttributeError):
                pass
            else:
                # Override all methods that alter data to raise an error
                # when they are called while the object is locked
                if callable(attr) and getattr(attr, 'alters_data', False):
                    setattr(cls, attr_name, LockableModel.__method_wrapper(attr_name))

    def lock(self) -> LockableModel:
        """
        Locks this object.
        Any future attempt to call a method that alters data (alters_data == True) on it will raise a RuntimeError.

        :return: This object.
        """
        self._locked = True
        return self  # Enable chaining

    @staticmethod
    def __method_wrapper(method_name: str):
        """
        Returns a wrapper function for the given method name.

        :param method_name: Method’s name.
        :return: The wrapper.
        """

        def wrapper(self, *args, **kwargs):
            if self._locked:
                raise RuntimeError('attempt to modify a locked object')
            else:
                return getattr(super(), method_name)(*args, **kwargs)

        return wrapper

    class Meta:
        abstract = True


# Disable default username validator
# Validation is handled by API
class CustomUser(dj_auth_models.AbstractUser, LockableModel):
    """Custom user class to override the default username validator."""
    username_validator = username_validator


class ModelWithRevisions(LockableModel):
    @property
    def latest_revision(self) -> typ.Optional[Revision]:
        """Returns the latest non-hidden revision for this page, or None if this page does not exist."""
        try:
            args = {
                self._revision_class().object_name(): self,
                'hidden': False,
            }
            return self._revision_class().objects.filter(**args).latest('date')
        except self._revision_class().DoesNotExist:
            return None

    def get_revision(self, revision_id: int) -> typ.Optional[Revision]:
        """Returns the revision with the given ID for this page, or None if the revision does not exist."""
        try:
            args = {
                self._revision_class().object_name(): self,
            }
            return self._revision_class().objects.filter(args).get(id=revision_id)
        except self._revision_class().DoesNotExist:
            return None

    @classmethod
    def _revision_class(cls) -> typ.Type[Revision]:
        """Associated Revision subclass. Every concrete subclass must implement this method."""
        raise NotImplementedError('_object_class')

    class Meta:
        abstract = True


class Page(ModelWithRevisions):
    """
    This class represents a wiki page.
    The actual content is handled by the PageRevision class.
    """
    namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    deleted = dj_models.BooleanField(default=False)
    content_model = dj_models.CharField(max_length=20, default=settings.PAGE_TYPE_WIKI,
                                        validators=[content_model_validator])
    content_language_code = dj_models.CharField(max_length=20, default=settings.DEFAULT_LANGUAGE_CODE,
                                                validators=[language_validator])

    @property
    def exists(self) -> bool:
        """Checks whether the page represented by this object actually exists, i.e. it has an ID and is not deleted."""
        return self.id is not None and not self.deleted

    @property
    def content_language(self) -> settings.i18n.Language:
        """Returns the language of this page’s content."""
        return settings.i18n.get_language(self.content_language_code)

    @property
    def url_title(self) -> str:
        """Returns the URL-compatible title for this page."""
        from .api import titles as api_titles
        return api_titles.as_url_title(self.title, escape=True)

    @property
    def full_title(self) -> str:
        """Returns the full title of this page."""
        from .api import titles as api_titles
        return api_titles.get_full_page_title(self.namespace_id, self.title)

    @property
    def url_full_title(self) -> str:
        """Returns the URL-compatible full title for this page."""
        from .api import titles as api_titles
        return api_titles.as_url_title(self.full_title, escape=True)

    @property
    def namespace(self) -> settings.Namespace:
        """Returns the namespace of this page as a Namespace object."""
        return settings.NAMESPACES[self.namespace_id]

    @property
    def subpage_title(self) -> typ.Tuple[typ.Optional[str], str]:
        """
        Returns the base title of this page.
        The base title is the part after the last / or the full title if there are no /
        or the namespace does not allow subpages.

        :return: A tuple containing the two parts of the title.
        First value may be None if there are no / or the namespace does not allow subpages.
        """
        ns = settings.NAMESPACES.get(self.namespace_id)
        if ns and ns.allows_subpages and '/' in self.title:
            # noinspection PyTypeChecker
            return tuple(self.title.rsplit('/', maxsplit=1))
        return None, self.title

    @property
    def is_category(self) -> bool:
        """Returns whether this page is a category."""
        return self.namespace_id == settings.CATEGORY_NS.id

    @property
    def is_maintenance_category(self) -> bool:
        """Returns whether this page is a maintenance category."""
        return self.is_category and CategoryData.objects.get(page=self).maintenance

    def get_categories(self) -> typ.Iterable[str]:
        """Returns all categories for this page."""
        return list(map(lambda pc: pc.category_name, PageCategory.objects.filter(page=self).order_by('category_name')))

    @classmethod
    def _revision_class(cls):
        return PageRevision

    class Meta:
        unique_together = ('namespace_id', 'title')


class CategoryData(LockableModel):
    """
    This class holds data for categories. Every Page instance in the Category namespace
    should have an associated instance of this class.
    """
    page = dj_models.OneToOneField(Page, dj_models.CASCADE)
    maintenance = dj_models.BooleanField(default=False)


class PageCategory(LockableModel):
    """
    This class associates pages with their categories.
    Each association may have a sort key.
    """
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE)
    # Do not link to Category object as pages might be associated to non-existant categories
    category_name = dj_models.CharField(max_length=Page._meta.get_field('title').max_length,
                                        validators=[page_title_validator])
    sort_key = dj_models.CharField(max_length=100, blank=True, null=True, default=None)

    class Meta:
        unique_together = ('page', 'category_name')


class Revision(LockableModel):
    """
    Base class for revisions.
    A revision is a version of a content like pages, messages or topics.
    A revision may be completely hidden or only its author and/or comment.
    """
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

    @classmethod
    def object_name(cls) -> str:
        """The name of the foreign key attribute. Must be implemented by all concrete subclasses."""
        raise NotImplementedError('object_name')

    @property
    def _object(self):
        return getattr(self, self.object_name())

    @property
    def _actual_class(self):
        return self.__class__

    def get_previous(self, ignore_hidden: bool = True) -> typ.Optional[Revision]:
        """
        Returns the revision preceding this one, if any.

        :param ignore_hidden: If true, hidden revisions will be skipped.
        :return: The previous revision or None if there aren’t any
        or all previous revisions are hidden and ignore_hidden is True.
        """
        try:
            params = {
                self.object_name(): self._object,
                'date__lt': self.date,
            }
            if ignore_hidden:
                params['hidden'] = False
            return self._actual_class.objects.filter(**params).latest('date')
        except self._actual_class.DoesNotExist:
            return None

    def get_next(self, ignore_hidden: bool = True) -> typ.Optional[Revision]:
        """
        Returns the revision following this one, if any.

        :param ignore_hidden: If true, hidden revisions will be skipped.
        :return: The next revision or None if there aren’t any
        or all next revisions are hidden and ignore_hidden is True.
        """
        params = {
            self.object_name(): self._object,
            'date__gt': self.date,
        }
        if ignore_hidden:
            params['hidden'] = False
        try:
            return self._actual_class.objects.filter(**params).earliest('date')
        except self._actual_class.DoesNotExist:
            return None

    def get_reverted_revision(self, ignore_hidden: bool = True) -> typ.Optional[Revision]:
        """
        Returns the revision this one reverted.

        :param ignore_hidden: If true and the reverted revision is hidden, None will be returned.
        :return: The revision that was reverted by this one, or None if there is none
        or it is hidden and ignore_hidden is True.
        """
        if self.reverted_to:
            params = {
                'id': self.reverted_to,
            }
            if ignore_hidden:
                params['hidden'] = False
            try:
                return self._actual_class.objects.filter(**params)
            except self._actual_class.DoesNotExist:
                pass
        return None

    @property
    def size(self) -> int:
        """Returns the content size of this revision, i.e. the number bytes in the content field."""
        return len(self.content.encode('utf-8'))

    @property
    def is_bot_edit(self) -> bool:
        """Returns whether this revision was made by a bot account."""
        return UserData.objects.get(user=self.author).is_in_group(settings.GROUP_BOTS)


class PageRevision(Revision):
    """This class represents a version of a wiki page."""
    page = dj_models.ForeignKey(Page, on_delete=dj_models.CASCADE)

    @classmethod
    def object_name(cls) -> str:
        return 'page'

    @property
    def has_created_page(self) -> bool:
        """Returns whether this revision created a new page."""
        return self.get_previous(ignore_hidden=False) is None


class PageProtectionStatus(LockableModel):
    """
    This class represents the protection status of a page.
    There should be at most one instance for a given page at all time.
    The protection level is the ID of the group whose users are allowed to edit the page.
    """
    # Do not link to Page object as non-existant pages might be protected
    page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    protection_level = dj_models.CharField(max_length=100, validators=[group_id_validator])
    applies_to_talk_page = dj_models.BooleanField()
    reason = dj_models.CharField(max_length=200)
    expiration_date = dj_models.DateField(blank=True, null=True, validators=[expiration_date_validator])

    class Meta:
        unique_together = ('page_namespace_id', 'page_title')


class TalkTopic(ModelWithRevisions):
    """
    A topic is attached to a page and groups messages.
    Topics may be nested to at most one parent topic.
    They may be deleted or pinned. Pinned topics are always displayed first in talk pages.
    """
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE)
    # Do not link to Page object as non-existant pages might have talks
    page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    parent_topic = dj_models.ForeignKey('self', dj_models.SET_NULL, null=True)
    pinned = dj_models.BooleanField(default=False)
    deleted = dj_models.BooleanField(default=False)

    @property
    def post_date(self) -> datetime.datetime:
        """Returns the date when this topic was created."""
        return self.talktopicrevision_set.earliest('date').date

    @property
    def last_updated(self) -> datetime.datetime:
        """Returns the date when this topic was last updated."""
        return self.talktopicrevision_set.latest('date').date

    @property
    def last_message_date(self) -> datetime.datetime:
        """Returns the date of the lastest updated message in this topic."""
        return self.message_set.latest('last_updated').date

    @classmethod
    def _revision_class(cls):
        return TalkTopicRevision


class TalkTopicRevision(Revision):
    """This class represents a version of a topic. The content attribute contains the title."""
    topic = dj_models.ForeignKey(TalkTopic, on_delete=dj_models.CASCADE)

    @classmethod
    def object_name(cls) -> str:
        return 'topic'

    @property
    def title(self) -> str:
        """Returns the topic’s title. Actually just an alias of the content attribute."""
        return self.content


class Message(ModelWithRevisions):
    """
    Messages are posted in talk pages and are attached to a single topic.
    A message can be a reply to at most one other message.
    They may be deleted.
    """
    topic = dj_models.ForeignKey(TalkTopic, dj_models.CASCADE)
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE)
    replied_to = dj_models.ForeignKey('self', dj_models.SET_NULL, null=True)
    deleted = dj_models.BooleanField(default=False)

    @property
    def post_date(self) -> datetime.datetime:
        """Returns the date when this message was posted."""
        return self.messagerevision_set.earliest('date').date

    @property
    def last_updated(self) -> datetime.datetime:
        """Returns the date when this message was last edited."""
        return self.messagerevision_set.latest('date').date

    @classmethod
    def _revision_class(cls):
        return MessageRevision


class MessageRevision(Revision):
    """This class represents a version of a message."""
    message = dj_models.ForeignKey(Message, on_delete=dj_models.CASCADE)

    @property
    def object_name(self) -> str:
        return 'message'


@dataclasses.dataclass(frozen=True)
class Gender:
    """Gender have two codes: one that identifies them, another for I18N."""
    code: str
    i18n_code: str


NEUTRAL_GENDER = Gender(code='neutral', i18n_code='neutral')
"""
Neutral/undefined gender.
Means the user has not defined their gender or they consider themselves neither male nor female.
"""
FEMALE_GENDER = Gender(code='female', i18n_code='feminine')
"""Female gender."""
MALE_GENDER = Gender(code='male', i18n_code='masculine')
"""Male gender."""
GENDERS = {gender.code: gender for gender in (NEUTRAL_GENDER, FEMALE_GENDER, MALE_GENDER)}
"""All defined genders associated to their code."""


# TODO make data accessible from JS API (read-only)?
class UserData(LockableModel):
    """
    This class holds all data for a specific user.
    Each user should be associated to exactly one instance of this class.
    """
    user = dj_models.OneToOneField(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    ip_address = dj_models.CharField(max_length=50, blank=True, null=True, default=None)

    # True = female, False = Male, None = Undefined
    _gender = dj_models.BooleanField(blank=True, null=True, default=None)
    """This user’s gender. Should not be edited directly."""
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
        """Is this user female?"""
        return self.gender == FEMALE_GENDER

    @property
    def is_male(self) -> bool:
        """Is this user male?"""
        return self.gender == MALE_GENDER

    @property
    def is_neutral_gender(self) -> bool:
        """Has this user chosen the neutral gender?"""
        return self.gender == NEUTRAL_GENDER

    @property
    def gender(self) -> Gender:
        """Returns the gender of this user."""
        if self._gender:
            return FEMALE_GENDER
        elif self._gender is not None:
            return MALE_GENDER
        return NEUTRAL_GENDER

    @gender.setter
    def gender(self, value: Gender):
        """Sets the gender of this user."""
        self._gender = {
            FEMALE_GENDER: True,
            MALE_GENDER: False,
            NEUTRAL_GENDER: None,
        }.get(value)

    @property
    def email_confirmed(self) -> bool:
        """Has this user confirmed their email address?"""
        return self.email_confirmation_date is not None

    @property
    def groups(self) -> typ.List[settings.UserGroup]:
        """Returns the list of all groups this user belongs to."""
        # noinspection PyUnresolvedReferences
        return [settings.GROUPS[rel.group_id] for rel in self.user.usergrouprel_set.filter(user=self.user)]

    @property
    def group_ids(self) -> typ.List[str]:
        """Returns the list of IDs of all groups this user belongs to."""
        # noinspection PyUnresolvedReferences
        return [rel.group_id for rel in self.user.usergrouprel_set.filter(user=self.user)]

    def is_in_group(self, group_id: str) -> bool:
        """
        Checks whether this user is in the given group.

        :param group_id: The group ID.
        :return: True if the user belongs to the group, False if they do not or the group ID does not exist.
        """
        group = settings.GROUPS.get(group_id)
        return group is not None and group in self.groups

    @property
    def prefered_language(self) -> settings.i18n.Language:
        """Returns this user’s prefered language."""
        return settings.i18n.get_language(self.lang_code)

    def get_datetime_format(self, language: settings.i18n.Language = None) -> str:
        """
        Returns the datetime format this user has chosen.

        :param language: If specified, this language will be used instead of the user’s prefered.
        :return: The datetime format.
        """
        formats = language.datetime_formats if language else self.prefered_language.datetime_formats
        if self.datetime_format_id is not None:
            format_id = self.datetime_format_id
        else:
            format_id = language.default_datetime_format_id
        return formats[format_id % len(formats)]

    @property
    def timezone_info(self) -> datetime.tzinfo:
        """Returns the timezone this user selected."""
        return pytz.timezone(self.timezone)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'UserData(user={self.user},ip_address={self.ip_address},gender={self._gender},skin={self.skin})'


class UserGroupRel(LockableModel):
    """This class associates users to groups."""
    user = dj_models.ForeignKey(dj_auth.get_user_model(), on_delete=dj_models.CASCADE)
    group_id = dj_models.CharField(max_length=20, validators=[group_id_validator])

    class Meta:
        unique_together = ('user', 'group_id')


class UserBlock(LockableModel):
    user = dj_models.OneToOneField(dj_auth.get_user_model(), dj_models.CASCADE)
    on_whole_site = dj_models.BooleanField(default=False)
    pages = dj_models.TextField()
    namespaces = dj_models.TextField()
    on_own_talk_page = dj_models.BooleanField(default=False)
    duration = dj_models.IntegerField()  # Days
    reason = dj_models.TextField(blank=True, null=True, default=None)

    @property
    def page_titles(self) -> typ.Iterable[str]:
        return self.pages.split(',')

    @property
    def namespace_ids(self) -> typ.Iterable[int]:
        return map(int, self.namespaces.split(','))


class User:
    """
    Simple wrapper class for Django users and their associated user data.
    The objects returned by the django_user and data properties will be locked.
    """

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
        """This user’s username."""
        return self.__django_user.username

    @property
    def prefered_language(self) -> settings.i18n.Language:
        """
        This user’s prefered language.
        If the user has not selected a prefered language, the default one is returned.
        """
        if self.__data:
            return self.__data.prefered_language
        else:
            return settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE)

    @property
    def groups(self) -> typ.List[settings.UserGroup]:
        """Returns the list of all groups this user belongs to."""
        return self.__data.groups

    @property
    def group_ids(self) -> typ.List[str]:
        """Returns the list of IDs of all groups this user belongs to."""
        return self.__data.group_ids

    @property
    def is_bot(self) -> bool:
        """Is this user a bot? A user is considered a bot if they belong to the 'bots' group."""
        return self.is_in_group(settings.GROUP_BOTS)

    @property
    def is_anonymous(self) -> bool:
        """Is this user anonymous? A user is considered anonymous if the ip_address field has a value."""
        return self.__data.ip_address is not None

    @property
    def is_logged_in(self) -> bool:
        """
        Is this user authenticated and logged in?
        A user is logged_in when they are authenticated and not anonymous.
        """
        return self.__django_user.is_authenticated and not self.is_anonymous

    def get_datetime_format(self, language: settings.i18n.Language = None) -> str:
        """
        Returns the datetime format this user has chosen.

        :param language: If specified, this language will be used instead of the user’s prefered.
        :return: The datetime format.
        """
        return self.data.get_datetime_format(language)

    def is_in_group(self, group_id: str) -> bool:
        """
        Checks whether this user is in the given group.

        :param group_id: The group ID.
        :return: True if the user belongs to the group, False if they do not or the group ID does not exist.
        """
        return self.__data.is_in_group(group_id)

    def has_right(self, right: str) -> bool:
        """
        Checks whether this group has the given right.

        :param right: The right to check.
        :return: True if the user is in any group that has the specified right.
        """
        return any(map(lambda g: g.has_right(right), self.__data.groups))

    # TODO prendre en compte les restrictions et blocages
    def can_read_page(self, namespace_id: int, title: str) -> bool:
        """
        Checks whether this user can read the given page.

        :param namespace_id: Page’s namespace ID.
        :param title: Page’s title.
        :return: True if the user can read the page, False otherwise.
        """
        return (self.has_right(settings.RIGHT_READ_PAGES) or
                (namespace_id == settings.USER_NS.id and re.fullmatch(fr'{self.username}(/.*)?', title)
                 or self.has_right(settings.RIGHT_EDIT_USER_PAGES)))

    # TODO prendre en compte les blocages
    def can_edit_page(self, namespace_id: int, title: str) -> typ.Tuple[bool, bool]:
        """
        Checks whether this user can edit the given page.

        :param namespace_id: Page’s namespace ID.
        :param title: Page’s title.
        :return: Two booleans indicating whether this user can edit the page or the talk page respectively.
        """
        try:
            page_protection = PageProtectionStatus.objects.get(page_namespace_id=namespace_id, page_title=title)
        except PageProtectionStatus.DoesNotExist:
            page_protection = None

        ns = settings.NAMESPACES[namespace_id]
        can_edit = (
                self.can_read_page(namespace_id, title)
                and (not page_protection or self.is_in_group(page_protection.protection_level))
                and (
                        (namespace_id == settings.USER_NS.id and re.fullmatch(fr'{self.username}(/.*)?', title))
                        or self.has_right(settings.RIGHT_EDIT_USER_PAGES)
                        or any(map(lambda g: g.can_edit_pages_in_namespace(ns), self.__data.groups))
                )
        )
        can_edit_talk = (
            (can_edit
             or not page_protection
             or not page_protection.applies_to_talk_page)
            # TODO and not is_redirect
        )
        return can_edit, can_edit_talk

    def __repr__(self):
        return f'User[django_user={self.__django_user.username},data={self.__data}]'


########
# Logs #
########


class LogEntry(LockableModel):
    """
    Base class for logs.
    Log entries are used to log most actions performed by users.
    """
    author = dj_models.ForeignKey(dj_auth.get_user_model(), dj_models.CASCADE, blank=True, null=True)
    date = dj_models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def format_key(self) -> str:
        """The I18N key to use when rendering this log entry. Should be implemented by concrete subclasses."""
        return ''

    @classmethod
    def search(cls, performer: str = None, from_date: datetime.date = None, to_date: datetime.date = None, **kwargs) \
            -> typ.Sequence[LogEntry]:
        """
        Returns log entries that match the given criteria.

        :param performer: The user performing this action.
        :param from_date: Return all entiers at and after this date.
        :param to_date: Return all entiers at and before this date.
        :param kwargs: Additional search criteria.
        :return: The matching log entries.
        """
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
    """Base class to user-related logs."""
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
    """Logs all user account creations."""
    automatic = dj_models.BooleanField()
    """Has the account been created by the server?"""

    @property
    def format_key(self) -> str:
        return f'log.{LOG_USER_CREATION}.entry' + ('_automatic' if self.automatic else '')

    @classmethod
    def search(cls, performer=None, from_date=None, to_date=None, **kwargs):
        # Ignore any additional criteria
        return super().search(performer, from_date, to_date)


class UserRenamingLogEntry(UserLogEntry):
    """Logs all user renames."""
    subject_new_username = dj_models.CharField(max_length=150)


class UserBlockLogEntry(UserLogEntry):
    """Logs all user blocks/unblocks"""
    expiration_date = dj_models.DateField(blank=True, null=True)
    # TODO add pages/namespaces


class UserGroupChangeLogEntry(UserLogEntry):
    """Logs all user-group changes."""
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
    """Base class for page-related logs."""
    # Do not link to Page object as non-existant/deleted pages might be concerned
    page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    reason = dj_models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def full_page_title(self):
        """Full title of the concerned page."""
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
    """Logs all page protection changes."""
    protection_level = dj_models.CharField(max_length=100, validators=[group_id_validator])
    expiration_date = dj_models.DateField(blank=True, null=True)
    applies_to_talk_page = dj_models.BooleanField()

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_PROTECTION}.entry' + ('' if self.expiration_date else '_no_date') + \
               ('_talk' if self.applies_to_talk_page else '')


class PageRenamingLogEntry(PageLogEntry):
    """Logs all page renames."""
    new_page_namespace_id = dj_models.IntegerField(validators=[namespace_id_validator])
    new_page_title = dj_models.CharField(max_length=100, validators=[page_title_validator])
    created_redirection = dj_models.BooleanField()
    moved_talks = dj_models.BooleanField()

    @property
    def new_full_page_title(self) -> str:
        from .api import titles as api_titles
        return api_titles.get_full_page_title(self.new_page_namespace_id, self.new_page_title)

    @property
    def format_key(self) -> str:
        return (f'log.{LOG_PAGE_RENAME}.entry'
                + ('_redirect' if self.created_redirection else '')
                + ('_moved_talks' if self.created_redirection else ''))


class PageDeletionLogEntry(PageLogEntry):
    """Logs all page deletions."""
    deleted = dj_models.BooleanField()

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_DELETION}.entry' + ('_deleted' if self.deleted else '_restored')


class PageCreationLogEntry(PageLogEntry):
    """Logs all page creations."""

    @property
    def format_key(self) -> str:
        return f'log.{LOG_PAGE_CREATION}.entry'


def register_journals(registry):
    """
    Registers all built-in journals.

    :param registry: The registry to use.
    """
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
