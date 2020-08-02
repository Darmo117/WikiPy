import logging
import random
import typing as typ
import sys
import re

import django.contrib.auth as dj_auth
import django.contrib.auth.models as dj_models
import django.db as dj_db

from . import _parser, _errors
from .. import models, skins, settings

REDIRECT_PATTERN = re.compile(r'@REDIRECT\[\[([^\n]+?)]]')

#########
# Users #
#########


INVALID_USERNAME = 'invalid username'
DUPLICATE_USERNAME = 'duplicate username'


def create_user(username: str, is_male: bool = None, email: str = None, password: str = None, ip: str = None) \
        -> typ.Union[str, dj_models.User]:
    anonymous = ip is not None
    if (not anonymous and username.startswith("Anonymous-")
            or '/' in username
            or settings.INVALID_TITLE_REGEX.search(username)):
        return INVALID_USERNAME
    else:
        if anonymous:
            email = None
            is_male = None
        try:
            user = dj_models.User.objects.create_user(username, email=email, password=password)
            user.save()
            models.UserData(user=user, is_male=is_male, ip_address=ip if anonymous else None).save()
            group_id = settings.GROUP_USERS if not anonymous else settings.GROUP_ALL
            models.UserGroupRel(user=user, group_id=group_id).save()
            logging.info(f'Created user {username}')
            return user
        except dj_db.IntegrityError:
            return DUPLICATE_USERNAME


def log_in(request, username: str, password: str) -> bool:
    return dj_auth.authenticate(request, username=username, password=password) is not None


def get_user(request) -> models.User:
    dj_user = dj_auth.get_user(request)

    if dj_user.is_anonymous:
        ip = request.META['REMOTE_ADDR']
        # Create user if IP and not already created
        if not ip_exists(ip):
            username = f'Anonymous-{random.randint(1, 1000)}'  # TODO revoir l’index
            dj_user = create_user(username, ip=ip)
        else:
            dj_user = dj_models.User.objects.get(userdata__ip_address=ip)

    user_data = models.UserData.objects.get(user=dj_user)
    return models.User(dj_user, user_data)


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
    return models.Page.objects.filter(namespace_id=namespace_id, title=title).count() != 0


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
    if m := REDIRECT_PATTERN.fullmatch(wikicode.strip()):
        title = m.group(1)
        try:
            check_title(title)
        except (_errors.BadTitleException, _errors.EmptyPageTitleException):
            pass
        else:
            return title
    return None


def render_wikicode(wikicode: str, skin_id: str) -> str:
    skin = skins.get_skin(skin_id)
    parser = _parser.WikicodeParser()
    parsed_wikicode = parser.parse_wikicode(wikicode)
    return skin.render_wikicode(sys.modules[__name__], parsed_wikicode)


# TODO gérer les conflits
def submit_page_content(namespace_id: int, title: str, user: models.User, wikicode: str, revision_id: int = None,
                        section_id: int = None):
    exists = page_exists(namespace_id, title)
    if exists:
        page = _get_page(namespace_id, title)
    else:
        page = models.Page(namespace_id=namespace_id, title=title)

    if not can_edit_page(user, namespace_id, title):
        raise _errors.PageEditForbidden(page)

    if not exists:
        page.save()

    if section_id is not None:
        latest_revision = page.get_latest_revision()
        header, sections = _parser.WikicodeParser.split_sections(latest_revision.content)
        sections[section_id] = wikicode
        new_content = _parser.WikicodeParser.paste_sections(header, sections)
        revision = models.PageRevision(page=page, author=user.django_user, content=new_content)
        revision.save()
    else:
        revision = models.PageRevision(page=page, author=user.django_user, content=wikicode)
        revision.save()
