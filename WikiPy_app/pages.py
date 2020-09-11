import string
import typing as typ

import django.utils.safestring as dj_safe

from . import api, settings, models, special_pages, page_context

FOUND = 200
FORBIDDEN = 403
NOT_FOUND = 404

READ = 'read'
EDIT = 'edit'
SUBMIT = 'submit'
HISTORY = 'history'
SPECIAL = 'special'
_SETUP = 'setup'


def get_main_page_title() -> str:
    return api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)


def get_setup_page(user: models.User) -> page_context.PageContext:
    return _get_base_page_context(-1, 'Setup', _SETUP, user, True, False, True, True, False)


def get_page(request, namespace_id: int, title: str, user: models.User, *, action: str = None,
             redirect_enabled: bool = True) -> typ.Tuple[typ.Union[page_context.PageContext, str], int]:
    if namespace_id != -1:
        page_exists = api.page_exists(namespace_id, title)
        can_edit = api.can_edit_page(user, namespace_id, title)
        can_read = api.can_read_page(user, namespace_id, title)
        revision_id = api.get_param(request.GET, 'revision_id', expected_type=int)

        if action == EDIT:
            return _get_edit_page(namespace_id, title, user, page_exists, can_read, can_edit, revision_id)
        elif action == HISTORY:
            return _get_page_history(namespace_id, title, user, page_exists, can_read, can_edit, request.GET)
        else:
            return _get_page(namespace_id, title, user, page_exists, can_read, can_edit, redirect_enabled, revision_id)
    else:
        return _get_special_page(title, user, api.page_exists(namespace_id, title), request)


def _get_special_page(title: str, user: models.User, page_exists: bool, request, **kwargs) \
        -> typ.Tuple[typ.Union[page_context.PageContext, str], int]:
    base_title = api.get_special_page_title(title)
    sub_title = api.get_special_page_sub_title(title)
    can_read = user.can_read_page(-1, base_title)

    if page_exists:
        if can_read:
            base_context = _get_base_page_context(-1, title, SPECIAL, user, True, False, page_exists, can_read, False)
            special_page = special_pages.get_special_page(base_title)
            data = special_page.get_data(api, sub_title, base_context, request, **kwargs)

            if hasattr(data, 'redirect'):
                return data.redirect, FOUND

            return data, FOUND
    return _get_page(-1, title, user, page_exists=False, can_read=can_read, can_edit=False, redirect_enabled=False)


def _get_page(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool, can_edit: bool,
              redirect_enabled: bool, revision_id: int = None) \
        -> typ.Tuple[typ.Union[page_context.PageContext, str], int]:
    redirect = None
    revision = None
    main_page = namespace_id == settings.MAIN_PAGE_NAMESPACE_ID and title == settings.MAIN_PAGE_TITLE
    if not page_exists:
        status = NOT_FOUND
        wikicode = api.get_page_content(4, 'Message-NoPage')[0]
    elif not can_read:
        status = FORBIDDEN
        wikicode = api.get_page_content(4, 'Message-ReadForbidden')[0]
    else:
        status = FOUND
        try:
            wikicode, revision = api.get_page_content(namespace_id, title, revision_id=revision_id)
            if revision.text_hidden and not user.has_right(settings.RIGHT_HIDE_REVISIONS):
                redirect = api.get_full_page_title(namespace_id, title)
            elif revision_id is None:
                redirect = api.get_redirect(wikicode)
        except api.RevisionDoesNotExist:
            wikicode = _format_message(api.get_page_content(4, 'Message-InvalidRevisionID')[0], revision_id=revision_id)

    if not redirect or not redirect_enabled:
        return _get_read_page_context(
            namespace_id,
            title,
            user,
            wikicode,
            status != FOUND or revision_id is not None,
            main_page and status == FOUND,
            status != NOT_FOUND,
            can_read,
            can_edit,
            revision=revision,
            archived=revision is not None and revision_id is not None
        ), status
    else:
        return redirect, FOUND


def _get_edit_page(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool, can_edit: bool,
                   revision_id: typ.Optional[int]) -> typ.Tuple[page_context.PageContext, int]:
    if can_edit or can_read:
        if not can_edit and not page_exists:
            error_message = _get_message(namespace_id, title, 'CreateForbidden', no_page_notice=True)
            return (_get_read_page_context(namespace_id, title, user, wikicode=error_message,
                                           noindex=True, is_main_page=False, page_exists=False, can_read=can_read,
                                           can_edit=False),
                    FORBIDDEN)

        if can_edit:
            edit_notice = _get_message(namespace_id, title, 'EditNotice')
        else:
            edit_notice = _get_message(namespace_id, title, 'EditForbidden')

        try:
            wikicode, revision = api.get_page_content(namespace_id, title, revision_id=revision_id)
            if revision and revision.text_hidden and not user.has_right(settings.RIGHT_HIDE_REVISIONS):
                raise api.RevisionDoesNotExist(revision_id)
            status = FOUND
        except api.RevisionDoesNotExist:
            wikicode = _format_message(api.get_page_content(4, 'Message-InvalidRevisionID')[0], revision_id=revision_id)
            revision = None
            status = NOT_FOUND

        return (_get_edit_page_context(namespace_id, title, user, wikicode, edit_notice, page_exists, can_read,
                                       can_edit, revision, revision is not None and revision_id is not None,
                                       error=status == NOT_FOUND),
                status)

    wikicode = _get_message(namespace_id, title, 'ReadForbidden')
    return (_get_read_page_context(namespace_id, title, user, wikicode, True, False, page_exists, False, False),
            FORBIDDEN)


def _get_page_history(namespace_id: int, title: str, user: models.User, page_exists: bool, can_read: bool,
                      can_edit: bool, url_params) -> typ.Tuple[page_context.PageContext, int]:
    if can_read:
        if page_exists:
            revisions = api.get_page_revisions(namespace_id, title, user)
            paginator, page = api.paginate(revisions, url_params)
            return (_get_page_history_context(namespace_id, title, user, can_read, can_edit, paginator, page, True),
                    FOUND)
        return (_get_page_history_context(namespace_id, title, user, can_read, can_edit, None, 0, False),
                NOT_FOUND)

    wikicode = _get_message(namespace_id, title, 'ReadForbidden')
    return (_get_read_page_context(namespace_id, title, user, wikicode, True, False, page_exists, False, False),
            FORBIDDEN)


def _get_message(namespace_id: int, title: str, notice_name: str, no_page_notice: bool = False) -> str:
    message = api.get_page_content(4, f'Message-{notice_name}')[0]
    ns_message = api.get_page_content(4, f'Message-{notice_name}-{namespace_id}')[0]
    if not no_page_notice:
        page_message = api.get_page_content(4, f'Message-{notice_name}-{namespace_id}-{title}')[0]
    else:
        page_message = ''

    if page_message:
        return page_message
    elif ns_message:
        return ns_message
    return message


def submit_page_content(request, namespace_id: int, title: str, user: models.User, wikicode: str, comment: str,
                        minor: bool, section_id: int = None) \
        -> typ.Tuple[typ.Tuple[page_context.PageContext, int], bool]:
    try:
        api.submit_page_content(namespace_id, title, user, wikicode, comment, minor, section_id=section_id)
        return get_page(request, namespace_id, title, user, redirect_enabled=False), True
    except api.PageEditForbidden:
        return get_page(request, namespace_id, title, user, action=EDIT), False
    except api.PageEditConflit:
        pass  # TODO handle conflicts


def get_bad_title_page(user: models.User, error: typ.Union[api.EmptyPageTitleException, api.BadTitleException],
                       request) -> page_context.PageContext:
    if isinstance(error, api.EmptyPageTitleException):
        return _get_special_page('Empty title', user, True, request)[0]
    elif isinstance(error, api.BadTitleException):
        return _get_special_page('Bad title', user, True, request, invalid_char=str(error))[0]
    else:
        raise ValueError('invalid error type')


def _format_message(page_content: str, **kwargs) -> str:
    return string.Template(page_content).safe_substitute(kwargs)


def _get_read_page_context(namespace_id: int, title: str, user: models.User, wikicode: str, noindex: bool,
                           is_main_page: bool, page_exists: bool, can_read: bool, can_edit: bool,
                           revision: models.PageRevision = None, archived: bool = False) \
        -> page_context.PageContext:
    base_context = _get_base_page_context(namespace_id, title, READ, user, noindex, is_main_page, page_exists, can_read,
                                          can_edit)
    render = dj_safe.mark_safe(api.render_wikicode(wikicode, user.data.skin))

    return page_context.ReadPageContext(base_context, wikicode=wikicode, revision=revision, archived=archived,
                                        rendered_page_content=render)


def _get_edit_page_context(namespace_id: int, title: str, user: models.User, wikicode: str, edit_notice: str,
                           page_exists: bool, can_read: bool, can_edit: bool, revision: models.PageRevision,
                           archived: bool, error: bool) \
        -> page_context.PageContext:
    base_context = _get_base_page_context(namespace_id, title, EDIT, user, True, False, page_exists, can_read, can_edit)
    edit_notice = dj_safe.mark_safe(api.render_wikicode(edit_notice, user.data.skin, disable_comment=True))
    if error:
        code = ''
        error_notice = dj_safe.mark_safe(api.render_wikicode(wikicode, user.data.skin, disable_comment=True))
    else:
        code = wikicode
        error_notice = ''

    return page_context.EditPageContext(base_context, wikicode=code, revision=revision, archived=archived,
                                        edit_notice=edit_notice, error_notice=error_notice)


def _get_page_history_context(namespace_id: int, title: str, user: models.User, can_read: bool, can_edit: bool,
                              paginator, page: int, page_exists: bool) \
        -> page_context.PageContext:
    base_context = _get_base_page_context(namespace_id, title, HISTORY, user, True, False, page_exists, can_read,
                                          can_edit)
    return page_context.ListPageContext(base_context, paginator=paginator, page=page)


def _get_base_page_context(namespace_id: int, title: str, mode: str, user: models.User, noindex: bool,
                           is_main_page: bool, page_exists: bool, can_read: bool, can_edit: bool) \
        -> page_context.PageContext:
    main_page_full_title = api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
    full_title = api.get_full_page_title(namespace_id, title)
    canonical_ns = api.get_namespace_name(namespace_id, local_name=False)
    ns_name = api.get_namespace_name(namespace_id)
    content_type = api.get_page_content_model(namespace_id, title)

    return page_context.PageContext(
        project_name=settings.PROJECT_NAME,
        main_page_namespace=settings.MAIN_PAGE_NAMESPACE_ID,
        main_page_title=settings.MAIN_PAGE_TITLE,
        main_page_title_url=api.as_url_title(settings.MAIN_PAGE_TITLE, escape=True),
        main_page_full_title=main_page_full_title,
        main_page_full_title_url=api.as_url_title(main_page_full_title, escape=True),
        page_title=title,
        page_title_url=api.as_url_title(title, escape=True),
        full_page_title=full_title,
        full_page_title_url=api.as_url_title(full_title, escape=True),
        namespace_id=namespace_id,
        canonical_namespace_name=canonical_ns,
        canonical_namespace_name_url=api.as_url_title(canonical_ns, escape=True),
        namespace_name=ns_name,
        namespace_name_url=api.as_url_title(ns_name, escape=True),
        mode=mode,
        noindex=noindex,
        show_title=not is_main_page or not settings.HIDE_TITLE_ON_MAIN_PAGE or not page_exists,
        language=settings.LANGUAGE_CODE,
        writing_direction=settings.WRITING_DIRECTION,
        user=user,
        skin_name=user.data.skin,
        page_exists=page_exists,
        user_can_read=can_read,
        user_can_edit=can_edit,
        user_can_hide=user.has_right(settings.RIGHT_HIDE_REVISIONS),
        content_type=content_type
    )
