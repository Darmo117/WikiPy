import typing as typ
from . import api, settings

FOUND = 200
NOT_FOUND = 404
FORBIDDEN = 403


def get_main_page_title() -> str:
    return api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)


def get_page(namespace_id: int, title: str, url_params: typ.Dict[str, str]) -> typ.Tuple[dict, int]:
    error_code = FOUND
    content = ''

    if not api.page_exists(namespace_id, title):
        error_code = NOT_FOUND
        content = api.get_page_content(4, 'Message-NoPage', default='')

    return _create_page_context(namespace_id, title, content, noindex=error_code != FOUND), error_code


def get_special_page(title: str, url_params: typ.Dict[str, str]) -> dict:
    pass


def _create_page_context(namespace_id: int, title: str, content: str, noindex=False):
    full_title = api.get_full_page_title(namespace_id, title)
    return {
        'project_name': settings.PROJECT_NAME,
        'full_page_title': full_title,
        'page_title': title,
        'page_content': content,
        'noindex': noindex,
    }
