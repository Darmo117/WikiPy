import re
import typing as typ

from . import api, settings, models, special_pages

FOUND = 200
FORBIDDEN = 403
NOT_FOUND = 404

READ = 'read'
EDIT = 'edit'
SUBMIT = 'submit'
HISTORY = 'history'
_SETUP = 'setup'


def get_main_page_title() -> str:
    return api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)


def get_page(request, namespace_id: int, title: str, user: models.User, *, action: str = None,
             redirect_enabled: bool = True) -> typ.Tuple[dict, int]:
    if namespace_id != -1:
        page_exists = api.page_exists(namespace_id, title)
        can_edit = api.can_edit_page(user, namespace_id, title)
        can_read = api.can_read_page(user, namespace_id, title)

        if action == EDIT:
            return _get_edit_page(namespace_id, title, user, page_exists, can_read, can_edit)
        elif action == HISTORY:
            return _get_page_history(namespace_id, title, user, page_exists, can_read, can_edit, request.GET)
        else:
            return _get_page(namespace_id, title, user, page_exists, can_read, can_edit, redirect_enabled)
    else:
        return _get_special_page(title, user, api.page_exists(namespace_id, title), request)


def get_setup_page(user: models.User):
    return _get_base_page_context(-1, 'Setup', _SETUP, user, True, False, True, True, False)


def _get_special_page(title: str, user: models.User, page_exists: bool, request) -> typ.Tuple[dict, int]:
    base_title = api.get_special_page_title(title)
    sub_title = api.get_special_page_sub_title(title)
    can_read = user.can_read_page(-1, base_title)

    if page_exists:
        if can_read:
            special_page = special_pages.get_special_page(base_title)
            data = special_page.get_data(api, sub_title, request)

            if data.get('redirect'):
                return data['redirect'], FOUND

            return _get_special_page_context(title, user, page_exists, can_read, special_page.id, data), FOUND
    return _get_page(-1, title, user, False, can_read, False, False)


def _get_page(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool, can_edit: bool,
              redirect_enabled: bool):
    redirect = None
    main_page = namespace_id == settings.MAIN_PAGE_NAMESPACE_ID and title == settings.MAIN_PAGE_TITLE
    if not page_exists:
        status = NOT_FOUND
        wikicode = api.get_page_content(4, 'Message-NoPage')
    elif not can_read:
        status = FORBIDDEN
        wikicode = api.get_page_content(4, 'Message-ReadForbidden')
    else:
        status = FOUND
        wikicode = api.get_page_content(namespace_id, title)
        redirect = api.get_redirect(wikicode)

    if not redirect or not redirect_enabled:
        return _get_read_page_context(namespace_id, title, user, wikicode, status != FOUND,
                                      main_page and status == FOUND, status != NOT_FOUND, can_read, can_edit), status
    else:
        return redirect, FOUND


def _get_edit_page(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool, can_edit: bool):
    if can_edit or can_read:
        if not can_edit and not page_exists:
            error_message = _get_message(namespace_id, title, 'CreateForbidden', no_page_notice=True)
            return _get_read_page_context(namespace_id, title, user, error_message, True, False, False, can_read,
                                          False), FORBIDDEN

        if can_edit:
            edit_notice = _get_message(namespace_id, title, 'EditNotice')
        else:
            edit_notice = _get_message(namespace_id, title, 'EditForbidden')

        wikicode = api.get_page_content(namespace_id, title)

        return _get_edit_page_context(namespace_id, title, user, wikicode, edit_notice, page_exists, can_read,
                                      can_edit), FOUND

    wikicode = _get_message(namespace_id, title, 'ReadForbidden')
    return _get_read_page_context(namespace_id, title, user, wikicode, True, False, page_exists, False,
                                  False), FORBIDDEN


def _get_page_history(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool,
                      can_edit: bool, url_params):
    if can_read:
        if page_exists:
            revisions = api.get_page_revisions(namespace_id, title)
            paginator, page = api.paginate(revisions, url_params)
            return _get_page_history_context(namespace_id, title, user, True, can_read, can_edit, paginator,
                                             page, True), FOUND
        return _get_page_history_context(namespace_id, title, user, True, can_read, can_edit, None,
                                         0, False), NOT_FOUND

    wikicode = _get_message(namespace_id, title, 'ReadForbidden')
    return _get_read_page_context(namespace_id, title, user, wikicode, True, False, page_exists, False,
                                  False), FORBIDDEN


def _get_message(namespace_id: int, title: str, notice_name: str, no_page_notice: bool = False) -> str:
    message = api.get_page_content(4, f'Message-{notice_name}')
    ns_message = api.get_page_content(4, f'Message-{notice_name}-{namespace_id}')
    if not no_page_notice:
        page_message = api.get_page_content(4, f'Message-{notice_name}-{namespace_id}-{title}')
    else:
        page_message = ''

    if page_message:
        return page_message
    elif ns_message:
        return ns_message
    return message


# TODO gérer les conflits
def submit_page_content(request, namespace_id: int, title: str, user: models.User, wikicode: str, comment: str,
                        minor: bool, section_id: int = None) -> typ.Tuple[typ.Tuple[dict, int], bool]:
    try:
        api.submit_page_content(namespace_id, title, user, wikicode, comment, minor, section_id=section_id)
        return get_page(request, namespace_id, title, user, redirect_enabled=False), True
    except api.PageEditForbidden:
        return get_page(request, namespace_id, title, user, action=EDIT), False
    except api.PageEditConflit:
        pass  # TODO


def get_bad_title_page(user: models.User, error: typ.Union[api.EmptyPageTitleException, api.BadTitleException]):
    if type(error) is api.EmptyPageTitleException:
        title = settings.i18n.trans('error.bad_title')
        wikicode = api.get_page_content(4, 'Message-EmptyTitle', default='')
    elif type(error) is api.BadTitleException:
        title = settings.i18n.trans('error.bad_title')
        wikicode = _message_format(api.get_page_content(4, 'Message-BadTitle', default=''), invalid_char=str(error))
    else:
        raise ValueError('invalid error type')

    return _get_read_page_context(-1, title, user, wikicode, True, False, True, True, False)


def _message_format(page_content: str, **kwargs) -> str:
    class DefaultDict(dict):
        def __missing__(self, key):
            return f'%({key})'

    # Add "s" after format placeholder then format
    try:
        return re.sub(r'(%\(\w+?\))', r'\1s', page_content) % DefaultDict(kwargs)
    except ValueError:
        return page_content


def _get_special_page_context(title: str, user: models.User, page_exists: bool, can_read: bool, page_id: str,
                              page_data: dict):
    base_context = _get_base_page_context(-1, title, READ, user, True, False, page_exists, can_read, False)
    return {
        **base_context,
        **page_data,
        'special_page': True,
        'special_page_name': page_id,
    }


def _get_read_page_context(namespace_id: int, title: str, user: models.User, wikicode: str, noindex: bool,
                           is_main_page: bool, page_exists: bool, can_read: bool, can_edit: bool,
                           revision_id: int = None):
    base_context = _get_base_page_context(namespace_id, title, READ, user, noindex, is_main_page, page_exists, can_read,
                                          can_edit)
    return {
        **base_context,
        'wikicode': wikicode,
        'revision_id': revision_id,
    }


def _get_edit_page_context(namespace_id: int, title: str, user: models.User, wikicode: str, edit_notice: str,
                           page_exists: bool, can_read: bool, can_edit: bool):
    base_context = _get_base_page_context(namespace_id, title, EDIT, user, True, False, page_exists, can_read, can_edit)
    return {
        **base_context,
        'wikicode': wikicode,
        'edit_notice': edit_notice,
    }


def _get_page_history_context(namespace_id: int, title: str, user: models.User, noindex: bool,
                              can_read: bool, can_edit: bool, paginator, page: int, page_exists: bool):
    base_context = _get_base_page_context(namespace_id, title, HISTORY, user, noindex, False, page_exists, can_read,
                                          can_edit)
    return {
        **base_context,
        'paginator': paginator,
        'page': page,
    }


def _get_base_page_context(namespace_id: int, title: str, mode: str, user: models.User, noindex: bool,
                           is_main_page: bool, page_exists: bool, can_read: bool, can_edit: bool) \
        -> typ.Dict[str, typ.Any]:
    full_title = api.get_full_page_title(namespace_id, title)
    return {
        'project_name': settings.PROJECT_NAME,
        'full_page_title': full_title,
        'full_page_title_url': api.as_url_title(full_title),
        'namespace_id': namespace_id,
        'page_title': title,
        'mode': mode,
        'noindex': noindex,
        'show_title': not is_main_page or not settings.HIDE_TITLE_ON_MAIN_PAGE or not page_exists,
        'language': settings.LANGUAGE,
        'writing_direction': settings.WRITING_DIRECTION,
        'wpy_user': user,
        'skin_name': user.data.skin,
        'page_exists': page_exists,
        'user_can_read': can_read,
        'user_can_edit': can_edit,
    }
