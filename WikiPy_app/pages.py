import typing as typ

from . import api, settings

FOUND = 200
NOT_FOUND = 404
FORBIDDEN = 403


def get_main_page_title() -> str:
    return api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)


def get_page(namespace_id: int, title: str, url_params: typ.Dict[str, str]) -> typ.Tuple[dict, int]:
    error_code = FOUND

    if not api.page_exists(namespace_id, title):
        error_code = NOT_FOUND
        content = api.get_page_content(4, 'Message-NoPage', default='')
    else:
        content = api.get_page_content(namespace_id, title)

    return _create_page_context(namespace_id, title, content, noindex=error_code != FOUND), error_code


def get_bad_title_page(error: ValueError):
    if type(error) is api.EmptyPageTitleException:
        title = settings.l10n.trans('error.bad_title.title')
        content = api.get_page_content(4, 'Message-EmptyTitle', default='')
    elif type(error) is api.BadTitleException:
        title = settings.l10n.trans('error.bad_title.title')
        content = api.get_page_content(4, 'Message-BadTitle', default='')
    else:
        raise ValueError('invalid error type')

    return _create_page_context(0, title, content, noindex=True)


def get_special_page(title: str, url_params: typ.Dict[str, str]) -> dict:
    pass


def _create_page_context(namespace_id: int, title: str, content: str, noindex=False, is_main_page=False):
    full_title = api.get_full_page_title(namespace_id, title)
    return {
        'project_name': settings.PROJECT_NAME,
        'full_page_title': full_title,
        'page_title': title,
        'page_content': content,
        'noindex': noindex,
        'is_main_page': is_main_page,
    }
