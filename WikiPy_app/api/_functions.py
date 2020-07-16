import typing as typ

from . import _parser as parser
from .. import models, skins, settings


def extract_namespace_name(full_title: str, local_name=True) -> str:
    return extract_namespace_and_title(full_title, local_name=local_name)[0]


def extract_namespace_id(full_title: str) -> int:
    return extract_namespace_and_title(full_title, ns_as_id=True)[0]


def extract_title(full_title: str) -> str:
    return extract_namespace_and_title(full_title)[1]


def extract_namespace_and_title(full_title: str, ns_as_id=False, local_name=True) \
        -> typ.Tuple[typ.Union[str, int], str]:
    split = full_title.split(':', maxsplit=1)
    if len(split) == 1:
        return '', split[0]
    ns_id = get_namespace_id(split[0])
    title = split[1]
    if ns_id is None:
        return '', split[0] + ':' + title
    return (get_namespace_name(ns_id, local_name=local_name), title) if not ns_as_id else (ns_id, title)


def get_full_page_title(namespace_id: int, title: str) -> str:
    return f'{settings.NAMESPACES[namespace_id]}:{title}'


def get_namespace_name(namespace_id: int, local_name=True) -> typ.Optional[str]:
    if namespace_id in settings.NAMESPACES:
        ns = settings.NAMESPACES[namespace_id]
        if local_name and 'local_names' in ns:
            return ns['local_names'][0]
        return ns['name']
    return None


def get_namespace_id(namespace_name: str) -> typ.Optional[int]:
    for ns_id, ns in settings.NAMESPACES.items():
        if ns['name'] == namespace_name or 'local_names' in ns and namespace_name in ns['local_names']:
            return ns_id
    return None


def page_exists(namespace_id: int, title: str) -> bool:
    return models.Page.objects.filter(namespace_id=namespace_id, title=title).count() != 0


def get_page_content(namespace_id: int, title: str, default=None) -> typ.Optional[str]:
    try:
        page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        return page.get_lastest_revision().content
    except models.PageRevision.DoesNotExist:
        return default


def render_wikicode(wikicode: str, skin_id: str) -> str:
    skin = skins.get_skin(skin_id)
    parsed_wikicode = parser.parse_wikicode(wikicode)
    return skin.render_wikicode(parsed_wikicode)
