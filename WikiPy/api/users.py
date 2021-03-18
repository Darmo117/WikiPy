import datetime
import logging
import re
import typing as typ

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.db.models as dj_db_models
import django.db.transaction as dj_db_trans

from . import emails, errors, logs
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
        password = password.strip()

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
    add_user_to_group(user, settings.GROUP_ALL, auto=True, reason=reason)
    if not anonymous:
        add_user_to_group(user, settings.GROUP_USERS, auto=True, reason=reason)

    logging.info(f'Successfully created user "{username}".')
    emails.send_email_change_confirmation_email(user, user.django_user.email)
    logging.info(f'Confirmation email sent.')

    return user


@dj_db_trans.atomic
def update_user_data(user: models.User, **kwargs) -> models.User:
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


def log_in(request, username: str, password: str) -> bool:
    user = dj_auth.authenticate(request, username=username, password=password)
    if user is not None:
        dj_auth.login(request, user)
        return True
    return False


def log_out(request):
    dj_auth.logout(request)


def get_user_from_request(request) -> models.User:
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
            return create_user(username, ip=ip)
        else:
            dj_user = dj_auth.get_user_model().objects.get(userdata__ip_address=ip)

    user_data = models.UserData.objects.get(user=dj_user)
    return models.User(dj_user, user_data)


def get_user_from_name(username: str) -> typ.Optional[models.User]:
    try:
        dj_user = dj_auth.get_user_model().objects.get(username__iexact=username)
        user_data = models.UserData.objects.get(user=dj_user)
        return models.User(dj_user, user_data)
    except dj_auth.get_user_model().DoesNotExist:
        return None


def get_user_gender_from_page(namespace_id: int, title: str) -> typ.Optional[models.Gender]:
    if namespace_id == settings.USER_NS.id:
        page_user = get_user_from_name(title.split('/')[0])
        return page_user.data.gender if page_user else None
    return None


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username__iexact=username).count() != 0


def ip_exists(ip: str) -> bool:
    return models.UserData.objects.filter(ip_address=ip).count() != 0


@dj_db_trans.atomic
def block_user(user: models.User, duration: int, reason: str, *, pages: typ.Iterable[str] = None,
               namespaces: typ.Iterable[int] = None):
    # TODO check rights
    for title in pages:
        models.UserBlock(user=user.data, duration=duration, reason=reason, pages=f'page:{title}').save()
    for ns_id in namespaces:
        models.UserBlock(user=user.data, duration=duration, reason=reason, pages=f'namespace:{ns_id}').save()
    # logs.add_log_entry(models.LOG_USER_BLOCK, user, reason=reason)  # TODO


def can_read_page(current_user: models.User, namespace_id: int, title: str) -> bool:
    return current_user.can_read_page(namespace_id, title)


def can_edit_page(current_user: models.User, namespace_id: int, title: str) -> bool:
    return current_user.can_edit_page(namespace_id, title)


def get_user_contributions(current_user: models.User, username: str, namespace: int = None,
                           only_hidden_revisions: bool = False, only_last_edits: bool = False,
                           only_page_creations: bool = False, hide_minor: bool = False,
                           from_date: datetime.date = None, to_date: datetime.date = None) \
        -> typ.Sequence[models.PageRevision]:
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
        can_hide = current_user.has_right(settings.RIGHT_HIDE_REVISIONS)
        for result in query_set:
            can_read = current_user.can_read_page(result.page.namespace_id, result.page.title)
            is_current = not result.get_next(ignore_hidden=not can_hide)
            if can_read and (not only_last_edits or is_current) and \
                    (not only_page_creations or result.has_created_page):
                result.lock()
                results.append(result)
        return results
    return []


@dj_db_trans.atomic
def add_user_to_group(user: models.User, group_id: str, performer: models.User = None, auto: bool = False,
                      reason: str = None) -> bool:
    if group_exists(group_id) and ((performer and performer.has_right(settings.RIGHT_EDIT_USERS_GROUPS)) or auto):
        models.UserGroupRel(user=user.django_user, group_id=group_id).save()
        logs.add_log_entry(models.LOG_USER_GROUP_CHANGE, performer, target_user=user.username, reason=reason,
                           group=group_id, joined=True)
        return True
    return False


@dj_db_trans.atomic
def remove_user_from_group(user: models.User, group_id: str, performer: models.User = None, auto: bool = False,
                           reason: str = None) -> bool:
    if group_exists(group_id) and ((performer and performer.has_right(settings.RIGHT_EDIT_USERS_GROUPS)) or auto):
        try:
            rel = models.UserGroupRel.objects.get(user=user.django_user, group_id=group_id)
        except models.UserGroupRel.DoesNotExist:
            pass
        else:
            rel.delete()
            logs.add_log_entry(models.LOG_USER_GROUP_CHANGE, performer, reason=reason, group=group_id, joined=False)
        return True
    return False


def group_exists(group_id: str) -> bool:
    return group_id in settings.GROUPS
