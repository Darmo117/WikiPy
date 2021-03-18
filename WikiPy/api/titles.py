import typing as typ
import urllib.parse as url_parse

import django.shortcuts as dj_scut

from . import errors, users
from .. import settings, special_pages, models


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
        return get_namespace_name(ns_id, local_name=local_name,
                                  gender=users.get_user_gender_from_page(ns_id, title)), title
    else:
        return ns_id, title


def get_full_page_title(namespace_id: int, title: str, local_name: bool = True) -> str:
    ns_name = get_namespace_name(namespace_id, local_name=local_name,
                                 gender=users.get_user_gender_from_page(namespace_id, title))
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
    # Convert first letter to caps if case sensitivity is disabled and not a user page
    elif not settings.CASE_SENSITIVE_TITLE and namespace_id != settings.USER_NS.id:
        def caps(s):
            return s[0].upper() + s[1:]

        ns = settings.NAMESPACES.get(namespace_id)
        if ns and ns.allows_subpages:
            title = '/'.join([caps(t) for t in title.split('/')])
        else:
            title = caps(title)

    return get_full_page_title(namespace_id, title)


def get_special_page_title(title: str) -> str:
    return title.split('/', 1)[0]


def get_special_page_sub_title(title: str) -> str:
    s = title.split('/', 1)
    return s[1] if len(s) > 1 else ''


def check_title(page_title: str):
    if page_title == '':
        raise errors.EmptyPageTitleException()
    if m := settings.INVALID_TITLE_REGEX.search(page_title):
        raise errors.BadTitleException(m.group(1))


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
