import datetime as dt
import logging
import random
import re
import sys
import typing as typ

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_models
import django.core.paginator as dj_page

from . import _parser, _errors
from .. import models, skins, settings, special_pages


#########
# Users #
#########


def create_user(username: str, is_male: bool = None, email: str = None, password: str = None, ip: str = None,
                ignore_email: bool = False) -> models.User:
    anonymous = ip is not None

    # TODO disable usernames that are equal without considering case
    if (not anonymous and username.startswith("Anonymous-")
            or '/' in username
            or settings.INVALID_TITLE_REGEX.search(username)):
        raise _errors.InvalidUsernameError(username)
    if get_user_from_name(username):
        raise _errors.DuplicateUsernameError(username)

    if anonymous:
        email = None
        is_male = None
    elif not ignore_email and not re.fullmatch(r'\w+([.-]\w+)*@\w+([.-]\w+)+', email):
        raise _errors.InvalidEmailError(email)
    elif password is None or password.strip() == '':
        raise _errors.InvalidPasswordError(password)

    if password is not None:
        password = password.strip()

    dj_user = dj_models.User.objects.create_user(username, email=email, password=password)
    dj_user.save()

    talk_text = settings.i18n.trans('link.talk')
    user_ns = get_namespace_name(6)
    user_talk_ns = get_namespace_name(7)
    kwargs = {
        'user': dj_user,
        'is_male': is_male,
        'ip_address': ip if anonymous else None,
        'timezone': settings.TIME_ZONE,
        'datetime_format': settings.DATETIME_FORMATS[0],
        'signature': f'[[{user_ns}:{username}|{username}]] ([[{user_talk_ns}:{username}|{talk_text}]])',
    }
    data = models.UserData(**kwargs)
    data.save()
    group_id = settings.GROUP_USERS if not anonymous else settings.GROUP_ALL
    models.UserGroupRel(user=dj_user, group_id=group_id).save()
    logging.info(f'Created user {username}')

    return models.User(dj_user, data)


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
            dj_user = dj_models.User.objects.get(userdata__ip_address=ip)

    user_data = models.UserData.objects.get(user=dj_user)
    return models.User(dj_user, user_data)


def get_user_from_name(username: str) -> typ.Optional[models.User]:
    try:
        dj_user = dj_models.User.objects.get(username__iexact=username)
        user_data = models.UserData.objects.get(user=dj_user)
        return models.User(dj_user, user_data)
    except dj_models.User.DoesNotExist:
        return None


def user_exists(username: str) -> bool:
    return dj_models.User.objects.filter(username=username).count() != 0


def ip_exists(ip: str) -> bool:
    return models.UserData.objects.filter(ip_address=ip).count() != 0


def block_user(user: models.User, duration: int, reason: str, *, pages: typ.Iterable[str] = None,
               namespaces: typ.Iterable[int] = None):
    for title in pages:
        models.UserBlock(user=user.data, duration=duration, reason=reason, pages=f'page:{title}').save()
    for ns_id in namespaces:
        models.UserBlock(user=user.data, duration=duration, reason=reason, pages=f'namespace:{ns_id}').save()


def can_read_page(user: models.User, namespace_id: int, title: str) -> bool:
    return user.can_read_page(namespace_id, title)


def can_edit_page(user: models.User, namespace_id: int, title: str) -> bool:
    return user.can_edit_page(namespace_id, title)


def get_user_contributions(username: str) -> typ.Iterable[models.PageRevision]:
    if user_exists(username):
        return models.PageRevision.objects.filter(author__username=username).order_by('-date')
    return []


def add_user_to_group(user: models.User, group_id: str, performer: models.User = None, setup: bool = False) \
        -> bool:
    if group_exists(group_id) and ((performer and performer.has_right(settings.RIGHT_EDIT_USERS_GROUPS)) or setup):
        models.UserGroupRel(user=user.django_user, group_id=group_id).save()
        return True

    return False


def group_exists(group_id: str) -> bool:
    return group_id in settings.GROUPS


def get_param(query_dict, param_name: str, expected_type: typ.Type[typ.Any] = str, default=None):
    try:
        value = query_dict.get(param_name, default)
        return expected_type(value) if value is not None else None
    except ValueError:
        return default


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
    main_ns = 0 if ns_as_id else get_namespace_name(0)

    split = full_title.split(':', maxsplit=1)

    if len(split) == 1:
        ns = main_ns
        title = split[0]
    else:
        ns = get_namespace_id(split[0])
        title = split[1]

        if ns is None:
            ns = main_ns
            title = split[0] + ':' + title

    return (get_namespace_name(ns, local_name=local_name), title) if not ns_as_id else (ns, title)


def get_full_page_title(namespace_id: int, title: str, local_name: bool = True) -> str:
    ns_name = get_namespace_name(namespace_id, local_name=local_name)
    if ns_name != '':
        return f'{ns_name}:{title}'
    return title


def get_namespace_name(namespace_id: int, local_name=True) -> typ.Optional[str]:
    if namespace_id in settings.NAMESPACES:
        ns = settings.NAMESPACES[namespace_id]
        return ns.get_name(local_name)
    return None


def get_namespace_id(namespace_name: str) -> typ.Optional[int]:
    for ns_id, ns in settings.NAMESPACES.items():
        if ns.matches_name(namespace_name):
            return ns_id
    return None


def get_actual_page_title(raw_title: str) -> str:
    namespace_id, title = extract_namespace_and_title(raw_title, ns_as_id=True)
    check_title(title)

    # Convert first letter to caps if case sensitivity is disabled
    if not settings.CASE_SENSITIVE_TITLE:
        title = title[0].upper() + title[1:]

    return get_full_page_title(namespace_id, title)


def check_title(page_title: str):
    if page_title == '':
        raise _errors.EmptyPageTitleException()
    if m := settings.INVALID_TITLE_REGEX.search(page_title):
        raise _errors.BadTitleException(m.group(1))


def as_url_title(full_page_title: str) -> str:
    return full_page_title.strip().replace(' ', '_')


def title_from_url(url_title: str) -> str:
    return url_title.replace('_', ' ').strip()


#########
# Pages #
#########


def paginate(values: typ.Iterable[typ.Any], url_params: typ.Dict[str, str]) -> typ.Tuple[dj_page.Paginator, int]:
    try:
        page = int(url_params.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1
    try:
        number_per_page = int(url_params.get('limit', 50))
        if number_per_page < 1:
            number_per_page = 1
        elif number_per_page > 500:
            number_per_page = 500
    except ValueError:
        number_per_page = 50

    return dj_page.Paginator(values, number_per_page), page


def get_base_page_namespace(namespace_id: int) -> typ.Optional[int]:
    if namespace_id == -1:
        return None
    ns = settings.NAMESPACES[namespace_id]
    return ns.id - 1 if ns.is_talk else ns.id


def get_talk_page_namespace(namespace_id: int) -> typ.Optional[int]:
    if namespace_id == -1:
        return None
    ns = settings.NAMESPACES[namespace_id]
    return ns.id if ns.is_talk else ns.id + 1


def page_exists(namespace_id: int, title: str) -> bool:
    if namespace_id != -1:
        return models.Page.objects.filter(namespace_id=namespace_id, title=title).count() != 0
    else:
        return special_pages.get_special_page(get_special_page_title(title)) is not None


def get_special_page_title(title: str) -> str:
    return title.split('/', 1)[0]


def get_special_page_sub_title(title: str) -> str:
    s = title.split('/', 1)
    return s[1] if len(s) > 1 else ''


def get_page_content(namespace_id: int, title: str, default='') -> str:
    if page_exists(namespace_id, title):
        page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        return page.get_latest_revision().content
    else:
        return default


def _get_page(namespace_id: int, title: str) -> models.Page:
    return models.Page.objects.get(namespace_id=namespace_id, title=title)


def get_page_revisions(namespace_id: int, title: str) -> typ.List[models.PageRevision]:
    return list(models.PageRevision.objects.filter(page=_get_page(namespace_id, title)).order_by('-date'))


def get_redirect(wikicode: str) -> typ.Optional[str]:
    return _PARSER.get_redirect(wikicode)


def format_datetime(datetime: dt.datetime, user: models.User):
    return datetime.strftime(user.data.datetime_format)


def render_wikicode(wikicode: str, skin_id: str) -> str:
    skin = skins.get_skin(skin_id)
    parsed_wikicode = _PARSER.parse_wikicode(wikicode)
    return skin.render_wikicode(_get_self(), parsed_wikicode)


# TODO gérer les conflits
def submit_page_content(namespace_id: int, title: str, user: models.User, wikicode: str, comment: typ.Optional[str],
                        minor: bool, section_id: int = None):
    exists = page_exists(namespace_id, title)
    if exists:
        page = _get_page(namespace_id, title)
    else:
        page = models.Page(namespace_id=namespace_id, title=title)

    if not can_edit_page(user, namespace_id, title):
        raise _errors.PageEditForbidden(page)

    if not exists:
        page.save()

    def _edit_size(old_text: str, new_text: str) -> int:
        return len(new_text.encode('UTF-8')) - len(old_text.encode('UTF-8'))

    latest_revision = page.get_latest_revision()
    prev_content = latest_revision.content if latest_revision else ''

    if section_id is not None:
        header, sections = _parser.WikicodeParser.split_sections(prev_content)
        sections[section_id] = wikicode
        new_content = _parser.WikicodeParser.paste_sections(header, sections)
        size = _edit_size(prev_content, new_content)
        revision = models.PageRevision(page=page, author=user.django_user, content=new_content, minor=minor, size=size)
        revision.save()
    else:
        size = _edit_size(prev_content, wikicode)
        revision = models.PageRevision(page=page, author=user.django_user, content=wikicode, comment=comment,
                                       minor=minor, diff_size=size)
        revision.save()


def _get_self():
    return sys.modules[__name__]


_PARSER = _parser.WikicodeParser(_get_self())
