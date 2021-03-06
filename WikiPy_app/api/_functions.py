import dataclasses
import datetime
import logging
import random
import typing as typ
import urllib.parse as url_parse

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.mail as dj_mail
import django.core.mail.backends.dummy as dj_mail_dummy
import django.core.paginator as dj_page
import django.core.validators as dj_valid
import django.db.models as dj_db_models
import django.db.transaction as dj_db_trans
import django.shortcuts as dj_scut
import django.utils.crypto as dj_crypto
import django.utils.timezone as dj_tz

from . import _errors, _diff
from .. import models, settings, special_pages, parser, media_backends, util

DiffType = _diff.DiffType

##########
# Emails #
##########

_EMAIL_CONNECTION = None


def open_email_connection():
    global _EMAIL_CONNECTION
    _EMAIL_CONNECTION = dj_mail.get_connection()


def is_email_connection_available() -> bool:
    return not isinstance(_EMAIL_CONNECTION, dj_mail_dummy.EmailBackend)


def generate_email_confirmation_code() -> str:
    return dj_crypto.get_random_string(length=30)


def send_email_change_confirmation_email(user: models.User, pending_email: str):
    user = update_user_data(
        user,
        email_pending_confirmation=pending_email
    )
    confirmation_code = generate_email_confirmation_code()
    update_user_data(user, email_confirmation_code=confirmation_code)
    link = get_page_url(settings.SPECIAL_NS.id, special_pages.get_special_page_for_id('change_email').get_title(),
                        confirm_code=confirmation_code, user=user.username)
    send_email(
        user.data.email_pending_confirmation,
        subject=user.prefered_language.translate('email.confirm_email.subject'),
        message=user.prefered_language.translate(
            'email.confirm_email.message',
            username=user.username,
            link=link
        )
    )


def send_email(to: typ.Union[str, models.User], subject: str, message: str):
    if hasattr(to, 'django_user'):
        recipient = to.django_user.email
    else:
        recipient = to
    dj_mail.send_mail(subject, message, from_email=None, recipient_list=[recipient])


def send_mass_email(recipients: typ.List[models.User], subject: str, message: str):
    datatuple = tuple(
        (subject, message, None, [to.django_user.email]) for to in recipients)
    dj_mail.send_mass_mail(datatuple)


#################
# Date and time #
#################


def now(timezone: datetime.tzinfo = None) -> datetime.datetime:
    if timezone:
        return dj_tz.make_naive(dj_tz.now(), timezone)
    return dj_tz.now()


def format_datetime(date_time: datetime.datetime, current_user: models.User, language: settings.i18n.Language,
                    custom_format: str = None) -> str:
    weekday = date_time.weekday() + 1  # Monday is 0
    month = date_time.month  # January is 1

    # Translate week day and month tags using current display language and not Python locale
    format_ = (custom_format or current_user.get_datetime_format(language)) \
        .replace('%a', language.get_day_abbreviation(weekday).replace('%', '%%')) \
        .replace('%A', language.get_day_name(weekday).replace('%', '%%')) \
        .replace('%b', language.get_month_abbreviation(month).replace('%', '%%')) \
        .replace('%B', language.get_month_name(month).replace('%', '%%'))
    # Disabled tags
    for tag_name in 'cxX':  # TODO raise exception
        format_ = format_.replace('%' + tag_name, '%%' + tag_name)

    return date_time.strftime(format_)


#########
# Users #
#########


def log_in_username_validator(value: str):
    if not user_exists(value):
        raise dj_exc.ValidationError('username does not exist', code='not_exists')


def username_validator(value: str, anonymous: bool = False):
    if (not anonymous and value.startswith('Anonymous-')
            or '/' in value
            or settings.INVALID_TITLE_REGEX.search(value)):
        raise dj_exc.ValidationError('invalid username', code='invalid')
    if user_exists(value):
        raise dj_exc.ValidationError('username already exists', code='duplicate')


def password_validator(value: str):
    if value is None or value.strip() == '':
        raise dj_exc.ValidationError('invalid')


def email_validator(value):
    dj_valid.EmailValidator()(value)


@dj_db_trans.atomic
def create_user(username: str, email: str = None, password: str = None, ip: str = None,
                ignore_email: bool = False) -> models.User:
    anonymous = ip is not None

    try:
        username_validator(username, anonymous=anonymous)
    except dj_exc.ValidationError as e:
        if e.code == 'invalid':
            raise _errors.InvalidUsernameError(username)
        elif e.code == 'duplicate':
            raise _errors.DuplicateUsernameError(username)

    if anonymous:
        email = None
        password = None
    else:
        try:
            password_validator(password)
        except dj_exc.ValidationError:
            raise _errors.InvalidPasswordError(password)
        password = password.strip()

        if not ignore_email:
            try:
                email_validator(email)
            except dj_exc.ValidationError:
                raise _errors.InvalidEmailError(email)

    dj_user = dj_auth.get_user_model().objects.create_user(username, email=email, password=password)
    dj_user.save()

    language = settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE)
    talk_text = language.translate('link.talk')
    user_ns = settings.USER_NS.get_name(local=True)
    user_talk_ns = settings.USER_TALK_NS.get_name(local=True)
    data = models.UserData(
        user=dj_user,
        ip_address=ip if anonymous else None,
        timezone=settings.TIME_ZONE,
        signature=f'[[{user_ns}:{username}|{username}]] ([[{user_talk_ns}:{username}|{talk_text}]])',
        max_image_file_preview_size=settings.IMAGE_PREVIEW_SIZES[6],
        max_image_thumbnail_size=settings.THUMBNAIL_SIZES[4]
    )
    data.save()
    user = models.User(dj_user, data)
    add_user_to_group(user, settings.GROUP_ALL, auto=True)
    if not anonymous:
        add_user_to_group(user, settings.GROUP_USERS, auto=True)
    logging.info(f'Successfully created user "{username}".')
    send_email_change_confirmation_email(user, user.django_user.email)
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
        'display_hidden_categories',
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
            username = f'Anonymous-{random.randint(1, 1000)}'  # TODO revoir l???index (utiliser un compteur)
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
    if namespace_id in (settings.USER_NS.id, settings.USER_TALK_NS.id):
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
def add_user_to_group(user: models.User, group_id: str, performer: models.User = None, auto: bool = False) \
        -> bool:
    if group_exists(group_id) and ((performer and performer.has_right(settings.RIGHT_EDIT_USERS_GROUPS)) or auto):
        models.UserGroupRel(user=user.django_user, group_id=group_id).save()
        return True
    return False


def group_exists(group_id: str) -> bool:
    return group_id in settings.GROUPS


##########
# Titles #
##########


def get_page_url(namespace_id: int, title: str, **kwargs) -> str:
    full_title = as_url_title(get_full_page_title(namespace_id, title))
    url = dj_scut.reverse('wikipy:page', kwargs={'raw_page_title': full_title})
    params = url_parse.urlencode({k: (v if not isinstance(v, list) else v[0]) for k, v in kwargs.items()})
    full_url = url + (('?' + params) if params else '')
    return full_url


def extract_namespace_name(full_title: str, local_name=True) -> str:
    return extract_namespace_and_title(full_title, local_name=local_name)[0]


def extract_namespace_id(full_title: str) -> int:
    return extract_namespace_and_title(full_title, ns_as_id=True)[0]


def extract_title(full_title: str) -> str:
    return extract_namespace_and_title(full_title)[1]


def extract_namespace_and_title(full_title: str, ns_as_id=False, local_name=True) \
        -> typ.Tuple[typ.Union[str, int], str]:
    main_ns = settings.MAIN_NS.id if ns_as_id else settings.MAIN_NS.get_name(local=local_name)

    split = tuple(map(str.strip, full_title.split(':', maxsplit=1)))

    if len(split) == 1:
        ns_id = main_ns
        title = split[0]
    else:
        ns_id = get_namespace_id(split[0])
        title = split[1]

        if ns_id is None:
            ns_id = main_ns
            title = split[0] + ':' + title

    if not ns_as_id:
        return get_namespace_name(ns_id, local_name=local_name, gender=get_user_gender_from_page(ns_id, title)), title
    else:
        return ns_id, title


def get_full_page_title(namespace_id: int, title: str, local_name: bool = True) -> str:
    ns_name = get_namespace_name(namespace_id, local_name=local_name,
                                 gender=get_user_gender_from_page(namespace_id, title))
    if ns_name != '':
        return f'{ns_name}:{title}'
    return title


def get_namespace_name(namespace_id: int, local_name: bool = True, gender: models.Gender = None) -> typ.Optional[str]:
    if namespace_id in settings.NAMESPACES:
        ns = settings.NAMESPACES[namespace_id]
        return ns.get_name(local=local_name, gender=gender)
    return None


def get_namespace_id(namespace_name: str) -> typ.Optional[int]:
    for ns_id, ns in settings.NAMESPACES.items():
        if ns.matches_name(namespace_name):
            return ns_id
    return None


def get_actual_page_title(raw_title: str) -> str:
    namespace_id, title = extract_namespace_and_title(raw_title, ns_as_id=True)
    check_title(title)

    if namespace_id == settings.SPECIAL_NS.id:
        base_title = get_special_page_title(title)
        sub_title = get_special_page_sub_title(title)
        if sp := special_pages.get_special_page(base_title):
            title = sp.get_title()
            if sub_title:
                title += '/' + sub_title
    # Convert first letter to caps if case sensitivity is disabled and not a user page/talk page
    elif not settings.CASE_SENSITIVE_TITLE and namespace_id not in (settings.USER_NS.id, settings.USER_TALK_NS.id):
        title = title[0].upper() + title[1:]

    return get_full_page_title(namespace_id, title)


def get_special_page_title(title: str) -> str:
    return title.split('/', 1)[0]


def get_special_page_sub_title(title: str) -> str:
    s = title.split('/', 1)
    return s[1] if len(s) > 1 else ''


def check_title(page_title: str):
    if page_title == '':
        raise _errors.EmptyPageTitleException()
    if m := settings.INVALID_TITLE_REGEX.search(page_title):
        raise _errors.BadTitleException(m.group(1))


def as_url_title(full_page_title: str, escape: bool = False) -> str:
    special_chars = [
        ('%', '%25'),
        ('&', '%26'),
        ('?', '%3F'),
        ('=', '%3D'),
    ]
    title = full_page_title.strip().replace(' ', '_')

    if escape:
        for c1, c2 in special_chars:
            title = title.replace(c1, c2)

    return title


def title_from_url(url_title: str) -> str:
    return url_title.replace('_', ' ').strip()


def get_wiki_url_path() -> str:
    return dj_scut.reverse('wikipy:page', kwargs={'raw_page_title': ''})


def get_api_url_path() -> str:
    return dj_scut.reverse('wikipy_api:index')


#########
# Pages #
#########


def get_page_content_type(content_model: str) -> str:
    return {
        settings.PAGE_TYPE_WIKI: 'text/plain',
        settings.PAGE_TYPE_STYLESHEET: 'text/css',
        settings.PAGE_TYPE_JAVASCRIPT: 'application/javascript',
    }.get(content_model, 'text/plain')


def get_diff(revision_id1: int, revision_id2: int, current_user: models.User, escape_html: bool, keep_lines: int) \
        -> typ.Tuple[_diff.DiffType, models.PageRevision, models.PageRevision, int]:
    try:
        revision1 = models.PageRevision.objects.get(id=revision_id1)
    except models.PageRevision.DoesNotExist:
        raise _errors.RevisionDoesNotExist(revision_id1)
    try:
        revision2 = models.PageRevision.objects.get(id=revision_id2)
    except models.PageRevision.DoesNotExist:
        raise _errors.RevisionDoesNotExist(revision_id2)

    page1 = revision1.page
    page2 = revision2.page

    if not current_user.can_read_page(page1.namespace_id, page1.title):
        raise _errors.PageReadForbidden(page1)
    if not current_user.can_read_page(page2.namespace_id, page2.title):
        raise _errors.PageReadForbidden(page2)

    if revision1.page.id == revision2.page.id:
        nb_not_shown = models.PageRevision.objects.filter(page=page1, date__gt=revision1.date,
                                                          date__lt=revision2.date).count()
    else:
        nb_not_shown = 0

    if revision1.content != revision2.content:
        diff = _diff.Diff(revision1, revision2).get(escape_html, keep_lines)
    else:
        diff = []

    revision1.lock()
    revision2.lock()
    return diff, revision1, revision2, nb_not_shown


def paginate(user: models.User, values: typ.Iterable[typ.Any], url_params: typ.Dict[str, str]) \
        -> typ.Tuple[dj_page.Paginator, int]:
    page = max(1, util.get_param(url_params, 'page', expected_type=int, default=1))
    number_per_page = min(settings.REVISIONS_LIST_PAGE_MAX,
                          max(settings.REVISIONS_LIST_PAGE_MIN,
                              util.get_param(url_params, 'limit', expected_type=int,
                                             default=user.data.default_revisions_list_size)))

    return dj_page.Paginator(values, number_per_page), page


@dataclasses.dataclass(frozen=True)
class SearchResult:
    namespace_id: int
    title: str
    date: datetime.datetime
    snapshot: str


def search(query: str, current_user: models.User, namespaces: typ.Iterable[int]) \
        -> typ.List[SearchResult]:
    results = []

    for ns, title, date, snapshot in _perform_search(query, current_user, namespaces=namespaces):
        results.append(SearchResult(
            namespace_id=ns,
            title=title,
            date=date,
            snapshot=snapshot
        ))

    return results


def _perform_search(query: str, current_user: models.User, namespaces: typ.Iterable[int]) \
        -> typ.List[typ.Tuple[int, str, datetime.datetime, str]]:
    ns_id, title = extract_namespace_and_title(query, ns_as_id=True)
    if ns_id:
        ns_list = [ns_id]
    else:
        ns_list = namespaces
    results = []

    for page in models.Page.objects.filter(title__icontains=title, namespace_id__in=ns_list):
        ns = page.namespace_id
        title = page.title
        if current_user.can_read_page(ns, title):
            revision = page.latest_revision
            snapshot = revision.content[:200]
            if snapshot != revision.content:
                snapshot += "???"
            results.append((ns, title, revision.date, snapshot))

    return results


def get_base_page_namespace(namespace_id: int) -> typ.Optional[int]:
    if namespace_id == settings.SPECIAL_NS.id:
        return None
    ns = settings.NAMESPACES[namespace_id]
    return ns.id - 1 if ns.is_talk else ns.id


def get_talk_page_namespace(namespace_id: int) -> typ.Optional[int]:
    if namespace_id == settings.SPECIAL_NS.id:
        return None
    ns = settings.NAMESPACES[namespace_id]
    return ns.id if ns.is_talk else ns.id + 1


def page_exists(namespace_id: int, title: str) -> bool:
    if namespace_id != settings.SPECIAL_NS.id:
        try:
            page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        except models.Page.DoesNotExist:
            return False
        return not page.deleted
    return special_pages.get_special_page(get_special_page_title(title)) is not None


def get_page_revision(namespace_id: int, title: str, *, revision_id: int = None) \
        -> typ.Optional[models.PageRevision]:
    if page_exists(namespace_id, title):
        page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        if revision_id is not None:
            revision = page.get_revision(revision_id)
        else:
            revision = page.latest_revision

        if not revision:
            raise _errors.RevisionDoesNotExist(revision_id)
        revision.lock()

        return revision
    else:
        return None


def get_page_revisions(page: models.Page, current_user: models.User) -> typ.List[models.PageRevision]:
    if page_exists(page.namespace_id, page.title) and current_user.can_read_page(page.namespace_id, page.title):
        revisions = models.PageRevision.objects.filter(page=page).order_by('-date')
        for r in revisions:
            r.lock()
        return list(revisions)
    return []


def get_page_categories(page: models.Page, get_hidden: bool) -> typ.List[typ.Tuple[models.Page, models.CategoryData]]:
    categories = []

    for c_name in page.get_categories():
        category_page, _ = get_page(settings.CATEGORY_NS.id, c_name)
        try:
            category_data = models.CategoryData.objects.get(page=category_page)
        except models.CategoryData.DoesNotExist:
            category_data = models.CategoryData(
                page=category_page
            )
            category_data.lock()
            categories.append((category_page, category_data))
        else:
            if get_hidden or not category_data.hidden:
                category_data.lock()
                categories.append((category_page, category_data))

    return categories


def get_random_page(namespaces: typ.Iterable[int] = None) -> typ.Optional[models.Page]:
    result = models.Page.objects.filter(namespace_id__in=namespaces)
    if result.count():
        page = random.choice(result)
        page.lock()
        return page
    return None


def get_redirect(wikicode: str) -> typ.Optional[typ.Tuple[str, typ.Optional[str]]]:
    return parser.WikicodeParser.get_redirect(wikicode)


_MEDIA_BACKEND = media_backends.get_backend(settings.MEDIA_BACKEND_ID)


def get_file_metadata(file_name: str) -> typ.Optional[media_backends.FileMetadata]:
    return _MEDIA_BACKEND.get_file_info(file_name)


def render_wikicode(wikicode: str, context, no_redirect: bool = False, enable_comment: bool = False) \
        -> typ.Union[str, typ.Tuple[str, bool]]:
    """
    Renders the given parsed wikicode.
    :param wikicode: The wikicode to render.
    :param context: The context to use for the render.
    :type context: WikiPy_app.page_context.PageContext
    :param no_redirect: If true and the wikicode is a redirection,
                        it will be rendered instead of rendering the page it points to.
    :param enable_comment: If true, the generation comment will be appended to the rendered HTML.
    :return: The wikicode rendered as HTML. If no_redirect is true, a boolean will also be returned, indicating whether
             the code is a redirection or not.
    """
    p = parser.WikicodeParser()
    parsed_wikicode = p.parse_wikicode(wikicode, context, no_redirect=no_redirect)
    render = context.skin.render_wikicode(parsed_wikicode, context, enable_comment=enable_comment)

    if no_redirect:
        return render, isinstance(parsed_wikicode, parser.RedirectNode)
    return render


def get_default_content_model(namespace_id: int, title: str):
    content_model = settings.PAGE_TYPE_WIKI
    allow_js_css = (namespace_id in [settings.WIKIPY_NS.id, settings.GADGET_NS.id] or
                    namespace_id == settings.USER_NS.id and '/' in title)
    if allow_js_css and title.endswith('.css'):
        content_model = settings.PAGE_TYPE_STYLESHEET
    elif allow_js_css and title.endswith('.js'):
        content_model = settings.PAGE_TYPE_JAVASCRIPT
    elif namespace_id == settings.MODULE_NS.id:
        content_model = settings.PAGE_TYPE_MODULE
    return content_model


# TODO handle conflicts
@dj_db_trans.atomic
def submit_page_content(context, namespace_id: int, title: str, current_user: models.User, wikicode: str,
                        comment: typ.Optional[str], minor: bool, section_id: int = None, hidden_category: bool = False):
    exists = page_exists(namespace_id, title)
    if exists:
        page = _get_page(namespace_id, title)
    else:
        page = models.Page(
            namespace_id=namespace_id,
            title=title,
            content_model=get_default_content_model(namespace_id, title),
            protection_level=settings.GROUP_ALL
        )

    if not can_edit_page(current_user, namespace_id, title):
        raise _errors.PageEditForbidden(page)

    if not exists:
        page.save()
        if namespace_id == settings.CATEGORY_NS.id:
            models.CategoryData(
                page=page,
                hidden=hidden_category
            ).save()
    elif namespace_id == settings.CATEGORY_NS.id:
        cd = models.CategoryData.objects.get(page=page)
        cd.hidden = hidden_category
        cd.save()

    def _set_page_categories(categories: typ.Dict[str, str]):
        # Add/update categories
        for category_name, sort_key in categories.items():
            pc, created = models.PageCategory.objects.get_or_create(
                page=page,
                category_name=category_name,
                defaults={
                    'sort_key': sort_key,
                }
            )
            if not created:
                pc.sort_key = sort_key
            pc.save()
        # Delete all categories that were removed
        for pc in models.PageCategory.objects.filter(page=page):
            if pc.category_name not in categories:
                pc.delete()

    def _edit_size(old_text: str, new_text: str) -> int:
        return len(new_text.encode('UTF-8')) - len(old_text.encode('UTF-8'))

    latest_revision = page.latest_revision
    prev_content = latest_revision.content if latest_revision else ''

    wikicode = wikicode.replace('\r\n', '\n')
    if section_id is not None:
        header, sections = parser.WikicodeParser.split_sections(prev_content)
        sections[section_id] = wikicode
        new_content = parser.WikicodeParser.paste_sections(header, sections)
    else:
        new_content = wikicode

    parser_ = parser.WikicodeParser()
    parser_.parse_wikicode(wikicode, context, no_redirect=True)
    # TODO categorize errors
    # cf. https://en.wikipedia.org/wiki/Category:Pages_where_template_include_size_is_exceeded
    too_many_transclusions = parser_.max_depth_reached
    too_many_redirects = parser_.too_many_redirects
    circular_transclusion = parser_.circular_transclusion_detected
    called_missing_template = parser_.called_non_existant_template
    _set_page_categories(parser_.categories)

    if prev_content != new_content:
        size = _edit_size(prev_content, wikicode)
        revision = models.PageRevision(page=page, author=current_user.django_user, content=wikicode, comment=comment,
                                       minor=minor, diff_size=size)
        revision.save()


def get_category_metadata(category_title: str) -> typ.Optional[models.CategoryData]:
    page, exists = get_page(settings.CATEGORY_NS.id, category_title)
    if exists and page.is_category:
        try:
            return models.CategoryData.objects.get(page__title=category_title)
        except models.CategoryData.DoesNotExist:
            return None
    return None


def get_page(namespace_id: int, title: str) -> typ.Tuple[models.Page, bool]:
    """
    Returns the page instance for the given namespace ID and title.
    The returned object will be uneditable.

    :param namespace_id: Page???s namespace ID.
    :param title: Page???s title.
    :return: The page and a boolean equal to True if the page exists or False otherwise.
    """
    if namespace_id != settings.SPECIAL_NS.id:
        page = _get_page(namespace_id, title)
        exists = page is not None and not page.deleted
        if not exists:
            page = models.Page(
                namespace_id=namespace_id,
                title=title,
                content_model=settings.PAGE_TYPE_WIKI
            )
    else:
        page = models.Page(namespace_id=settings.SPECIAL_NS.id, title=title)
        exists = page_exists(settings.SPECIAL_NS.id, title)
    page.lock()
    return page, exists


####################
# Helper functions #
####################


def get_message(notice_name: str) -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
    if revision:
        return revision.content, revision.page.content_language
    return '', None


def get_page_message(page: models.Page, notice_name: str, no_page_notice: bool = False) \
        -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    if page.namespace_id != settings.SPECIAL_NS.id:
        message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
        ns_message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}-{page.namespace_id}')
        if not no_page_notice:
            page_message_revision = get_page_revision(settings.WIKIPY_NS.id,
                                                      f'Message-{notice_name}-{page.namespace_id}-{page.title}')
        else:
            page_message_revision = None

        if page_message_revision:
            return page_message_revision.content, page_message_revision.page.content_language
        elif ns_message_revision:
            return ns_message_revision.content, ns_message_revision.page.content_language
        elif message_revision:
            return message_revision.content, message_revision.page.content_language
    return '', None


def _get_page(namespace_id: int, title: str) -> typ.Optional[models.Page]:
    """
    Returns the page instance for the given namespace ID and title.

    :param namespace_id: Page???s namespace ID.
    :param title: Page???s title.
    :return: The page or None if it doesn???t exist.
    """
    try:
        return models.Page.objects.get(namespace_id=namespace_id, title=title)
    except models.Page.DoesNotExist:
        return None
