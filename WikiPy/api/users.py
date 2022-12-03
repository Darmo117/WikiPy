"""
This module defines functions related to users.
"""
import datetime
import logging
import re
import typing as typ

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.handlers.wsgi as dj_wsgi
import django.db.models as dj_db_models
import django.db.transaction as dj_db_trans

from . import emails, errors, logs, _action
from .. import models, settings


def log_in_username_validator(value: str):
    if not user_exists(value):
        raise dj_exc.ValidationError('username does not exist', code='not_exists')


def username_validator(value: str, anonymous: bool = False):
    models.username_validator(value, anonymous)
    if user_exists(value):
        raise dj_exc.ValidationError('username already exists', code='duplicate')


password_validator = models.password_validator
email_validator = models.email_validator


@dj_db_trans.atomic
def create_user(username: str, email: str = None, password: str = None, ip: str = None,
                ignore_email: bool = False) -> models.User:
    """
    Creates a new user account.
    Automated backend accounts should only specify username and a password and set ignore_email to True.
    The IP address should not be used outside of this API.

    :param username: Account’s username.
    :param email: Account’s email address.
    :param password: Account’s password.
    :param ip: Account’s IP address. Only used for anonymous accounts.
    :param ignore_email: If true, the email address will be ignored. Only used for the wiki setup account.
    :return: The generated User object.
    :raises InvalidUsernameError: If the username is invalid.
    :raises DuplicateUsernameError: If the username already exists.
    :raises InvalidPasswordError: If the password is invalid.
    :raises InvalidEmailError: If the email address is invalid.
    """
    from . import titles

    anonymous = ip is not None

    try:
        username_validator(username, anonymous=anonymous)
    except dj_exc.ValidationError as e:
        if e.code == 'invalid':
            raise errors.InvalidUsernameError(username)
        elif e.code == 'duplicate':
            raise errors.DuplicateUsernameError(username)
        else:
            raise e

    if anonymous:
        email = None
        password = None
    else:
        try:
            models.password_validator(password)
        except dj_exc.ValidationError:
            raise errors.InvalidPasswordError(password)

        if not ignore_email:
            try:
                models.email_validator(email)
            except dj_exc.ValidationError:
                raise errors.InvalidEmailError(email)

    dj_user = dj_auth.get_user_model().objects.create_user(username, email=email, password=password)
    dj_user.save()

    language = settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE)
    data = models.UserData(
        user=dj_user,
        ip_address=ip if anonymous else None,
        timezone=settings.TIME_ZONE,
        signature=' ',  # Actual signature is set after saving once
        max_image_file_preview_size=settings.IMAGE_PREVIEW_SIZES[6],
        max_image_thumbnail_size=settings.THUMBNAIL_SIZES[4]
    )
    data.save()
    talk_text = language.translate('link.talk')
    user_link = titles.get_full_page_title(settings.USER_NS.id, username)
    talk_link = titles.get_wiki_url_path() + user_link
    data.signature = f'[[{user_link}|{username}]] ([({talk_link}|{talk_text})])'
    data.save()

    user = models.User(dj_user, data)
    logs.add_log_entry(models.LOG_USER_CREATION, user, automatic=ignore_email or anonymous)
    reason = settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE).translate('log.user_creation.reason')
    add_user_to_group(user, settings.GROUP_ALL, performer=None, auto=True, reason=reason)
    if not anonymous:
        add_user_to_group(user, settings.GROUP_USERS, performer=None, auto=True, reason=reason)

    logging.info(f'Successfully created user "{username}".')
    emails.send_email_change_confirmation_email(user, user.django_user.email)
    logging.info(f'Confirmation email sent.')

    return user


@_action.api_action()
@dj_db_trans.atomic
def update_user_data(user: models.User, *, performer: models.User = None, auto: bool = False, **kwargs) -> models.User:
    """
    Updates the preferences for the given user.

    :param user: The user to update.
    :param kwargs: The updated user data.
    :param performer: The user performing this action.
    :param auto: If true, the performer parameter will be ignored. For internal API use only!
    :return: The updated user.
    :raises ValueError: If kwargs contains an illegal attribute.
    """
    if not auto:
        if performer.django_user.id == user.django_user.id:
            _action.check_rights(performer, settings.RIGHT_EDIT_MY_PREFERENCES)
        else:
            raise errors.ActionError('cannot edit preferences of others')

    allowed_fields = (
        'lang_code',
        'signature',
        'gender',
        'email_pending_confirmation',
        'email_confirmation_date',
        'email_confirmation_code',
        'users_can_send_emails',
        'send_copy_of_sent_emails',
        'send_watchlist_emails',
        'send_minor_watchlist_emails',

        'skin',
        'datetime_format_id',
        'timezone',
        'max_image_file_preview_size',
        'max_image_thumbnail_size',
        'enable_media_viewer',
        'display_maintenance_categories',
        'numbered_section_titles',
        'confirm_rollback',

        'default_revisions_list_size',
        'all_edits_minor',
        'blank_comment_prompt',
        'unsaved_changes_warning',
        'show_preview_first_edit',
        'preview_above_edit_box',

        'rc_max_days',
        'rc_max_revisions',
        'rc_group_by_page',
        'rc_hide_minor',
        'rc_hide_categories',
        'rc_hide_patrolled',
        'rc_hide_patrolled_new_pages',

        'django_email',
    )
    django_user = dj_auth.get_user_model().objects.get(username=user.username)
    user_data = models.UserData.objects.get(user__username=user.username)
    dj_changed = False
    data_changed = False

    for k, v in kwargs.items():
        if k not in allowed_fields:
            raise ValueError(f'attempted to set disallowed field "{k}" for user "{user.username}"')
        if k.startswith('django_'):
            setattr(django_user, k[7:], v)
            dj_changed = True
        else:
            setattr(user_data, k, v)
            data_changed = True

    if dj_changed:
        django_user.save()
    if data_changed:
        user_data.save()

    return get_user_from_name(user.username)


@dj_db_trans.atomic
def log_in(request: dj_wsgi.WSGIRequest, username: str, password: str) -> bool:
    """
    Authenticates then logs in the user from the given request using the specified username and password.

    :param request: The HTTP request.
    :param username: User’s username.
    :param password: User’s password.
    :return: True if the user was successfully authenticated and logged in, false otherwise.
    """
    user = dj_auth.authenticate(request, username=username, password=password)
    if user is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request: dj_wsgi.WSGIRequest):
    """
    Logs out the user from the given request.

    :param request: The HTTP request.
    """
    dj_auth.logout(request)


@dj_db_trans.atomic
def get_user_from_request(request: dj_wsgi.WSGIRequest) -> models.User:
    """
    Returns the user from the given request.
    If the user is not logged in and their IP address is not registered, a new Anonymous account will be created.
    This account will be named Anonymous-<id> with id being an auto-incremented integer value starting from 1.

    :param request: The HTTP request.
    :return: The User object.
    """
    dj_user = dj_auth.get_user(request)

    if dj_user.is_anonymous:
        ip = request.META['REMOTE_ADDR']
        # Create user if IP and not already created
        if not ip_exists(ip):
            if models.UserData.objects.count():
                def f(ud: models.UserData) -> int:
                    return int(re.fullmatch(r'Anonymous-(\d+)', ud.user.username)[1])

                i = max(map(f, models.UserData.objects.filter(user__username__startswith='Anonymous-')))
            else:
                i = 1
            username = f'Anonymous-{i}'
            # No need to check for errors
            return create_user(username, ip=ip)
        else:
            dj_user = dj_auth.get_user_model().objects.get(userdata__ip_address=ip)

    user_data = models.UserData.objects.get(user=dj_user)
    return models.User(dj_user, user_data)


def get_user_from_name(username: str) -> typ.Optional[models.User]:
    """
    Returns the User object for the given username.

    :param username: The username.
    :return: The User object or None if no account with this username exists.
    """
    try:
        dj_user = dj_auth.get_user_model().objects.get(username__iexact=username)
        user_data = models.UserData.objects.get(user=dj_user)
        return models.User(dj_user, user_data)
    except dj_auth.get_user_model().DoesNotExist:
        return None


def get_user_gender_from_page(namespace_id: int, title: str) -> typ.Optional[models.Gender]:
    """
    Returns the gender for the given user page.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The gender or None if the page is not a user page or the user does not exist.
    """
    if namespace_id == settings.USER_NS.id:
        page_user = get_user_from_name(title.split('/')[0])
        return page_user.data.gender if page_user else None
    return None


def user_exists(username: str) -> bool:
    """
    Checks whether an account exists for the given username.

    :param username: The username to check.
    :return: True if an account exists, false otherwise.
    """
    return dj_auth.get_user_model().objects.filter(username__iexact=username).count() != 0


def ip_exists(ip: str) -> bool:
    """
    Checks whether the given IP address is registered.

    :param ip: The IP address to check.
    :return: True if the IP address is registered, false otherwise.
    """
    return models.UserData.objects.filter(ip_address=ip).count() != 0


@_action.api_action(settings.RIGHT_BLOCK_USERS)
@dj_db_trans.atomic
def block_user(user_to_block: models.User, duration: int, reason: str, *, performer: models.User,
               on_pages: typ.Iterable[str] = None, on_namespaces: typ.Iterable[int] = None,
               on_own_talk_page: bool = False, on_whole_site: bool = False):
    """
    Blocks the given user on the specified pages and/or namespaces for the given duration.

    :param user_to_block: The user to block.
    :param duration: The duration in days.
    :param reason: Reason for blocking this user.
    :param performer: The user performing this action.
    :param on_pages: The pages on which this user will be blocked. Ignored if on_whole_site is true.
    :param on_namespaces: The namespaces on which this user will be blocked. Ignored if on_whole_site is true.
    :param on_own_talk_page: If true, the user will not be able to edit its own talk page.
    Ignored if on_whole_site is true.
    :param on_whole_site: If true, the user will be blocked on the whole wiki.
    :raises MissingRightError: If the current user does not have the permission to block/unblock users.
    """
    if on_whole_site:
        models.UserBlock(user=user_to_block.django_user, duration=duration, reason=reason, on_whole_site=True).save()
    else:
        models.UserBlock(
            user=user_to_block.django_user,
            duration=duration,
            reason=reason,
            on_own_talk_page=on_own_talk_page,
            pages=','.join(on_pages),
            namespaces=','.join(map(str, on_namespaces))
        ).save()
    # logs.add_log_entry(models.LOG_USER_BLOCK, performer, user, reason=reason)  # TODO


@_action.api_action(settings.RIGHT_BLOCK_USERS)
@dj_db_trans.atomic
def unblock_user(reason: str, block_id: int, *, performer: models.User):
    """
    Deletes the given user block.

    :param reason: Reason for deleting this user block.
    :param block_id: User block ID.
    :param performer: The user performing this action.
    :raises MissingRightError: If the current user does not have the permission to block/unblock users.
    """
    try:
        block = models.UserBlock.objects.get(id=block_id)
    except models.UserBlock.DoesNotExist:
        raise errors.UserBlockDoesNotExistError(block_id)
    else:
        unblocked_user = get_user_from_name(block.user.username)
        block.delete()
        # TODO log


@_action.api_action()
def get_user_contributions(current_user: models.User, username: str, namespace: int = None,
                           only_hidden_revisions: bool = False, only_last_edits: bool = False,
                           only_page_creations: bool = False, hide_minor: bool = False, hide_messages: bool = False,
                           from_date: datetime.date = None, to_date: datetime.date = None) \
        -> typ.Sequence[typ.Union[models.PageRevision, models.MessageRevision]]:
    """
    Returns the contributions of the given user.

    :param current_user: The current user.
    :param username: The user to get the contributions of.
    :param namespace: Only return edits on pages in this namespace.
    :param only_hidden_revisions: Only return hidden revisions.
    Will not return anything if current_user does not have the permission to hide revisions.
    :param only_last_edits: Only return edits that are current.
    :param only_page_creations: Only return edits that created a page.
    :param hide_minor: Do not return minor edits.
    :param hide_messages: Do not return message edits.
    :param from_date: Only return edits at or after this date.
    :param to_date: Only return edits at or before this date.
    :return: The list of revisions.
    """
    if user_exists(username):
        kwargs = {
            'author__username': username,
        }
        if namespace is not None:
            kwargs['page__namespace_id'] = namespace
        if hide_minor:
            kwargs['minor'] = False
        if from_date:
            kwargs['date__gte'] = from_date
        if to_date:
            kwargs['date__lte'] = datetime.datetime(to_date.year, to_date.month, to_date.day, hour=23, minute=59,
                                                    second=59)
        query = dj_db_models.Q(**kwargs)
        if only_hidden_revisions:
            query = query & (dj_db_models.Q(text_hidden=True) |
                             dj_db_models.Q(author_hidden=True) |
                             dj_db_models.Q(comment_hidden=True))

        query_set = models.PageRevision.objects.filter(query).order_by('-date')
        results = []
        can_hide = current_user.has_right(settings.RIGHT_DELETE_REVISIONS)
        for result in query_set:
            can_read = current_user.can_read_page(result.page.namespace_id, result.page.title)
            is_current = not result.get_next(ignore_hidden=not can_hide)
            if can_read and (not only_last_edits or is_current) and \
                    (not only_page_creations or result.has_created_page):
                result.lock()
                results.append(result)

        # TODO add messages if hide_messages is False

        return results
    return []


@_action.api_action()
@dj_db_trans.atomic
def add_user_to_group(user: models.User, group_id: str, *, performer: models.User = None, auto: bool = False,
                      reason: str = None):
    """
    Adds the given user to a group.

    :param user: The user to add to the group.
    :param group_id: The group ID.
    :param performer: The user performing this action.
    :param auto: Is the operation made by the server? If true, the performer argument will be ignored.
    :param reason: Reason for adding the user to this group.
    :raises MissingRightError: If auto is False and the performer does not have the permission to edit users’ groups.
    """
    if performer and not auto:
        _action.check_rights(performer, settings.RIGHT_EDIT_USERS_GROUPS)
    if not group_exists(group_id):
        raise ValueError(f'group with ID {group_id} does not exist')

    models.UserGroupRel(user=user.django_user, group_id=group_id).save()
    logs.add_log_entry(models.LOG_USER_GROUP_CHANGE, performer, target_user=user.username, reason=reason,
                       group=group_id, joined=True)


@_action.api_action()
@dj_db_trans.atomic
def remove_user_from_group(user: models.User, group_id: str, *, performer: models.User = None, auto: bool = False,
                           reason: str = None):
    """
    Removes the given user from a group.

    :param user: The user to add to the group.
    :param group_id: The group ID.
    :param performer: The user performing this action.
    :param auto: Is the operation made by the server? If true, the performer argument will be ignored.
    :param reason: Reason for adding the user to this group.
    :raises MissingRightError: If auto is False and the performer does not have the permission to edit users’ groups.
    """
    if performer and not auto:
        _action.check_rights(performer, settings.RIGHT_EDIT_USERS_GROUPS)
    if not group_exists(group_id):
        raise ValueError(f'group with ID {group_id} does not exist')

    try:
        rel = models.UserGroupRel.objects.get(user=user.django_user, group_id=group_id)
    except models.UserGroupRel.DoesNotExist:
        pass
    else:
        rel.delete()
        logs.add_log_entry(models.LOG_USER_GROUP_CHANGE, performer, reason=reason, group=group_id, joined=False)


def group_exists(group_id: str) -> bool:
    """
    Checks whether a group ID exists.

    :param group_id: The group ID to check.
    :return: True if a group with this ID exists, false otherwise.
    """
    return group_id in settings.GROUPS
