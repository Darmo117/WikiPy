import dataclasses
import datetime as dt
import logging
import random
import typing as typ

import django.contrib.auth as dj_auth
import django.core.exceptions as dj_exc
import django.core.paginator as dj_page
import django.core.validators as dj_valid
import django.db.models as dj_db

from . import _errors, _diff
from .. import models, skins, settings, special_pages, parser, media_backends, util

DiffType = _diff.DiffType


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


def create_user(username: str, is_male: bool = None, email: str = None, password: str = None, ip: str = None,
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
        is_male = None
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

    talk_text = settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE).translate('link.talk')
    user_ns = settings.USER_NS.get_name(local=True)
    user_talk_ns = settings.USER_NS_TALK.get_name(local=True)
    kwargs = {
        'user': dj_user,
        'is_male': is_male,
        'ip_address': ip if anonymous else None,
        'timezone': settings.TIME_ZONE,
        'datetime_format_id': 0,
        'signature': f'[[{user_ns}:{username}|{username}]] ([[{user_talk_ns}:{username}|{talk_text}]])',
    }
    data = models.UserData(**kwargs)
    data.save()
    user = models.User(dj_user, data)
    add_user_to_group(user, settings.GROUP_ALL, auto=True)
    if not anonymous:
        add_user_to_group(user, settings.GROUP_USERS, auto=True)
    logging.info(f'Created user {username}')

    return user


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
            username = f'Anonymous-{random.randint(1, 1000)}'  # TODO revoir l’index (utiliser un compteur)
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


def user_exists(username: str) -> bool:
    return dj_auth.get_user_model().objects.filter(username__iexact=username).count() != 0


def ip_exists(ip: str) -> bool:
    return models.UserData.objects.filter(ip_address=ip).count() != 0


def block_user(user: models.User, duration: int, reason: str, *, pages: typ.Iterable[str] = None,
               namespaces: typ.Iterable[int] = None):
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
                           only_page_creations: bool = False, hide_minor: bool = False, from_date: dt.date = None,
                           to_date: dt.date = None) \
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
            kwargs['date__lte'] = dt.datetime(to_date.year, to_date.month, to_date.day, hour=23, minute=59, second=59)
        query = dj_db.Q(**kwargs)
        if only_hidden_revisions:
            query = query & (dj_db.Q(text_hidden=True) | dj_db.Q(author_hidden=True) | dj_db.Q(comment_hidden=True))

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


def extract_namespace_name(full_title: str, local_name=True) -> str:
    return extract_namespace_and_title(full_title, local_name=local_name)[0]


def extract_namespace_id(full_title: str) -> int:
    return extract_namespace_and_title(full_title, ns_as_id=True)[0]


def extract_title(full_title: str) -> str:
    return extract_namespace_and_title(full_title)[1]


def extract_namespace_and_title(full_title: str, ns_as_id=False, local_name=True) \
        -> typ.Tuple[typ.Union[str, int], str]:
    main_ns = settings.MAIN_NS.id if ns_as_id else settings.MAIN_NS.get_name(local=local_name)

    split = full_title.split(':', maxsplit=1)

    if len(split) == 1:
        ns_id = main_ns
        title = split[0]
    else:
        ns_id = get_namespace_id(split[0])
        title = split[1]

        if ns_id is None:
            ns_id = main_ns
            title = split[0] + ':' + title

    return (get_namespace_name(ns_id, local_name=local_name), title) if not ns_as_id else (ns_id, title)


def get_full_page_title(namespace_id: int, title: str, local_name: bool = True) -> str:
    ns_name = get_namespace_name(namespace_id, local_name=local_name)
    if ns_name != '':
        return f'{ns_name}:{title}'
    return title


def get_namespace_name(namespace_id: int, local_name=True) -> typ.Optional[str]:
    if namespace_id in settings.NAMESPACES:
        ns = settings.NAMESPACES[namespace_id]
        return ns.get_name(local=local_name)
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
    elif not settings.CASE_SENSITIVE_TITLE and namespace_id not in (settings.USER_NS.id, settings.USER_NS_TALK.id):
        title = title[0].upper() + title[1:]

    return get_full_page_title(namespace_id, title)


def get_special_page_title(title: str) -> str:
    return title.split('/', 1)[0]


def get_special_page_sub_title(title: str) -> str:
    s = title.split('/', 1)
    return s[1] if len(s) > 1 else ''


def get_page_content_type(content_model: str) -> str:
    return {
        'wiki_page': 'text/plain',
        'css': 'text/css',
        'js': 'application/javascript',
    }.get(content_model, 'text/plain')


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


#########
# Pages #
#########


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


def paginate(values: typ.Iterable[typ.Any], url_params: typ.Dict[str, str]) -> typ.Tuple[dj_page.Paginator, int]:
    page = min(1, util.get_param(url_params, 'page', expected_type=int, default=1))
    number_per_page = min(500, max(1, util.get_param(url_params, 'limit', expected_type=int, default=50)))

    return dj_page.Paginator(values, number_per_page), page


@dataclasses.dataclass(frozen=True)
class SearchResult:
    namespace_id: int
    title: str
    date: dt.datetime
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
        -> typ.List[typ.Tuple[int, str, dt.datetime, str]]:
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
                snapshot += "…"
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
        return models.Page.objects.filter(namespace_id=namespace_id, title=title).count() != 0
    else:
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


def get_random_page(namespaces: typ.Iterable[int] = None) -> typ.Optional[models.Page]:
    result = models.Page.objects.filter(namespace_id__in=namespaces)
    if result.count():
        page = random.choice(result)
        page.lock()
        return page
    return None


def get_redirect(wikicode: str) -> typ.Optional[typ.Tuple[str, typ.Optional[str]]]:
    return parser.WikicodeParser.get_redirect(wikicode)


def format_datetime(datetime: dt.datetime, current_user: models.User):
    # TODO traduire le nom des mois
    return datetime.strftime(current_user.datetime_format)


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
    if p.max_depth_reached:
        # TODO catégoriser (permettre de spécifier le nom depuis une page du ns WikiPy)
        # cf. https://en.wikipedia.org/wiki/Category:Pages_where_template_include_size_is_exceeded
        pass
    render = context.skin.render_wikicode(parsed_wikicode, context, enable_comment=enable_comment)

    if no_redirect:
        return render, isinstance(parsed_wikicode, parser.RedirectNode)
    return render


# TODO gérer les conflits
def submit_page_content(namespace_id: int, title: str, current_user: models.User, wikicode: str,
                        comment: typ.Optional[str], minor: bool, section_id: int = None):
    exists = page_exists(namespace_id, title)
    if exists:
        page = _get_page(namespace_id, title)
    else:
        content_model = settings.PAGE_TYPE_WIKI
        is_user_or_wpy_ns = namespace_id in [settings.USER_NS.id, settings.WIKIPY_NS.id] and '/' in title
        if is_user_or_wpy_ns and title.endswith('.css'):
            content_model = settings.PAGE_TYPE_STYLESHEET
        elif is_user_or_wpy_ns and title.endswith('.js'):
            content_model = settings.PAGE_TYPE_JAVASCRIPT
        elif namespace_id == settings.MODULE_NS.id:
            content_model = settings.PAGE_TYPE_MODULE
        page = models.Page(namespace_id=namespace_id, title=title, content_model=content_model)

    if not can_edit_page(current_user, namespace_id, title):
        raise _errors.PageEditForbidden(page)

    if not exists:
        page.save()

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

    if prev_content != new_content:
        size = _edit_size(prev_content, wikicode)
        revision = models.PageRevision(page=page, author=current_user.django_user, content=wikicode, comment=comment,
                                       minor=minor, diff_size=size)
        revision.save()


def get_page(namespace_id: int, title: str) -> typ.Tuple[models.Page, bool]:
    """
    Returns the page instance for the given namespace ID and title.
    The returned object will be uneditable.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page and a boolean equal to True if the page exists or False otherwise.
    """
    if namespace_id != settings.SPECIAL_NS.id:
        page = _get_page(namespace_id, title)
        exists = page is not None
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

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page or None if it doesn’t exist.
    """
    try:
        return models.Page.objects.get(namespace_id=namespace_id, title=title)
    except models.Page.DoesNotExist:
        return None
