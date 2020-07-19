import typing as typ

from . import _parser, _errors
from .. import models, skins, settings


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
        return main_ns, split[0]

    ns_id = get_namespace_id(split[0])
    title = split[1]

    if ns_id is None:
        return main_ns, split[0] + ':' + title
    return (get_namespace_name(ns_id, local_name=local_name), title) if not ns_as_id else (ns_id, title)


def get_full_page_title(namespace_id: int, title: str) -> str:
    ns_name = get_namespace_name(namespace_id)
    if ns_name != '':
        return f'{ns_name}:{title}'
    return title


def get_namespace_name(namespace_id: int, local_name=True) -> typ.Optional[str]:
    if namespace_id in settings.NAMESPACES:
        ns = settings.NAMESPACES[namespace_id]
        if namespace_id != 0 and local_name and 'local_names' in ns:
            return ns['local_names'][0]
        return ns['name']
    return None


def get_namespace_id(namespace_name: str) -> typ.Optional[int]:
    for ns_id, ns in settings.NAMESPACES.items():
        if ns['name'].lower() == namespace_name.lower() or \
                'local_names' in ns and namespace_name.lower() in map(str.lower, ns['local_names']):
            return ns_id
    return None


def page_exists(namespace_id: int, title: str) -> bool:
    return models.Page.objects.filter(namespace_id=namespace_id, title=title).count() != 0


def get_page_content(namespace_id: int, title: str, default=None) -> typ.Optional[str]:
    try:
        page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        return page.get_latest_revision().content
    except models.Page.DoesNotExist:
        return default


def get_actual_page_title(raw_title: str) -> str:
    namespace_id, title = extract_namespace_and_title(raw_title, ns_as_id=True)
    check_title(title)
    return get_full_page_title(namespace_id, title)


def check_title(page_title: str):
    if page_title == '':
        raise _errors.EmptyPageTitleException()
    if settings.INVALID_TITLE_REGEX.search(page_title):
        raise _errors.BadTitleException()


def as_url_title(full_page_title: str) -> str:
    return full_page_title.strip().replace(' ', '_')


def title_from_url(url_title: str) -> str:
    return url_title.replace('_', ' ').strip()


def render_wikicode(wikicode: str, skin_id: str) -> str:
    skin = skins.get_skin(skin_id)
    parsed_wikicode = _parser.parse_wikicode(wikicode)
    return skin.render_wikicode(parsed_wikicode)
