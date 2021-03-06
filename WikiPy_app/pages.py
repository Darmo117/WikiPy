import string
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.utils.safestring as dj_safe
import pygments
import pygments.formatters as pyg_format
import pygments.lexers as pyg_lex

from . import api, settings, models, special_pages, page_context, forms, util, skins

FOUND = 200
FORBIDDEN = 403
NOT_FOUND = 404

READ = 'read'
EDIT = 'edit'
SUBMIT = 'submit'
HISTORY = 'history'
SPECIAL = 'special'
SETUP = 'setup'


def get_main_page_title() -> str:
    return api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)


def get_setup_page_context(request: dj_wsgi.WSGIRequest, user: models.User, language: settings.i18n.Language,
                           skin: str) -> page_context.PageContext:
    page, _ = api.get_page(settings.SPECIAL_NS.id, 'Setup')
    return _get_base_page_context(
        request,
        page=page,
        mode=SETUP,
        user=user,
        language=language,
        content_language=language,
        skin=skin,
        noindex=True,
        page_exists=True,
        can_read=True,
        can_edit=False
    )


def get_page_context(
        request: dj_wsgi.WSGIRequest,
        namespace_id: int,
        title: str,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        *,
        action: str = None,
        redirect_enabled: bool = True,
        redirects_list: typ.List[str] = None,
        form: forms.EditPageForm = None
) -> typ.Tuple[page_context.PageContext, int]:
    if namespace_id != settings.SPECIAL_NS.id:
        page, page_exists = api.get_page(namespace_id, title)
        if not page_exists:
            page.content_model = api.get_default_content_model(namespace_id, title)
        can_edit = api.can_edit_page(user, namespace_id, title)
        can_read = api.can_read_page(user, namespace_id, title)
        revision_id = util.get_param(request.GET, 'revision_id', expected_type=int)

        if action == EDIT:
            return _get_edit_page(
                request,
                page=page,
                user=user,
                language=language,
                skin=skin,
                page_exists=page_exists,
                can_read=can_read,
                can_edit=can_edit,
                revision_id=revision_id,
                form=form
            )
        elif action == HISTORY:
            return _get_page_history(
                request,
                page=page,
                user=user,
                language=language,
                skin=skin,
                page_exists=page_exists,
                can_read=can_read,
                can_edit=can_edit,
                url_params=request.GET
            )
        else:
            return _get_page(
                request,
                page=page,
                user=user,
                language=language,
                skin=skin,
                page_exists=page_exists,
                can_read=can_read,
                can_edit=can_edit,
                redirect_enabled=redirect_enabled,
                redirects_list=redirects_list,
                revision_id=revision_id,
                raw=action == 'raw'
            )
    else:
        return _get_special_page_context(title, user, language, skin, request)


def _get_special_page_context(
        title: str,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        request: dj_wsgi.WSGIRequest,
        **kwargs
) -> typ.Tuple[page_context.PageContext, int]:
    base_title = api.get_special_page_title(title)
    sub_title = api.get_special_page_sub_title(title)
    page, page_exists = api.get_page(settings.SPECIAL_NS.id, title)

    if page_exists:
        special_page = special_pages.get_special_page(base_title)
        base_context = _get_base_page_context(
            request,
            page=page,
            mode=SPECIAL,
            user=user,
            language=language,
            content_language=language,
            skin=skin,
            noindex=True,
            page_exists=True,
            can_read=True,
            can_edit=False
        )
        context = special_page.get_data(sub_title, base_context, request, **kwargs)
        return context, FOUND

    return _get_page(
        request,
        page=page,
        user=user,
        language=language,
        skin=skin,
        page_exists=False,
        can_read=True,
        can_edit=False,
        redirect_enabled=False
    )


def _get_page(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        page_exists: bool,
        can_read: bool,
        can_edit: bool,
        redirect_enabled: bool,
        redirects_list: typ.List[str] = None,
        revision_id: int = None,
        raw: bool = False
) -> typ.Tuple[page_context.PageContext, int]:
    redirect = None
    redirect_anchor = None
    display_redirect = False
    revision = None

    if not page_exists:
        status = NOT_FOUND
        if page.namespace_id == settings.SPECIAL_NS.id:
            wikicode, page_lang = api.get_message('NoSpecialPage')
        else:
            wikicode, page_lang = api.get_message('NoPage')
    elif not can_read:
        status = FORBIDDEN
        wikicode, page_lang = api.get_message('ReadForbidden')
    else:
        status = FOUND
        try:
            revision = api.get_page_revision(page.namespace_id, page.title, revision_id=revision_id)
            revision.lock()
            wikicode = revision.content
            page_lang = page.content_language
            if revision.text_hidden and not user.has_right(settings.RIGHT_HIDE_REVISIONS):
                redirect = page.full_title
            elif revision_id is None:
                redir = api.get_redirect(wikicode)
                if redir:
                    display_redirect = True
                    redirect, redirect_anchor = redir
                    if redirect in (redirects_list or []):
                        redirect_enabled = False
        except api.RevisionDoesNotExist:
            wikicode, page_lang = api.get_message('InvalidRevisionID')
            wikicode = _format_message(wikicode, revision_id=revision_id)

    context = _get_read_page_context(
        request,
        page=page,
        user=user,
        language=language,
        content_language=page_lang or language,
        skin=skin,
        wikicode=wikicode,
        noindex=status != FOUND or revision_id is not None,
        page_exists=status != NOT_FOUND,
        can_read=can_read,
        can_edit=can_edit,
        revision=revision,
        archived=revision is not None and revision_id is not None,
        redirected_from=redirects_list[0] if redirects_list else None,
        raw=raw
    )

    if not redirect or not redirect_enabled:
        return context, status
    else:
        return page_context.RedirectPageContext(context, redirect, anchor=redirect_anchor,
                                                display=display_redirect), FOUND


def _get_edit_page(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        page_exists: bool,
        can_read: bool,
        can_edit: bool,
        revision_id: int = None,
        form: forms.EditPageForm = None
) -> typ.Tuple[page_context.PageContext, int]:
    if can_edit or can_read:
        if not can_edit and not page_exists:
            error_message, page_lang = api.get_page_message(page, 'CreateForbidden', no_page_notice=True)
            return (_get_read_page_context(
                request,
                page=page,
                user=user,
                language=language,
                content_language=page_lang or language,
                skin=skin,
                wikicode=error_message,
                noindex=True,
                page_exists=False,
                can_read=can_read,
                can_edit=False
            ), FORBIDDEN)

        if can_edit:
            edit_notice = api.get_page_message(page, 'EditNotice')[0]
        else:
            edit_notice = api.get_page_message(page, 'EditForbidden')[0]

        try:
            revision = api.get_page_revision(page.namespace_id, page.title, revision_id=revision_id)
            if revision and revision.text_hidden and not user.has_right(settings.RIGHT_HIDE_REVISIONS):
                raise api.RevisionDoesNotExist(revision_id)
            elif revision:
                wikicode = revision.content
            else:
                wikicode = ''
            status = FOUND
        except api.RevisionDoesNotExist:
            r = api.get_page_revision(settings.WIKIPY_NS.id, 'Message-InvalidRevisionID')
            if r:
                wikicode = _format_message(r.content, revision_id=revision_id)
            else:
                wikicode = ''
            revision = None
            status = NOT_FOUND

        return (_get_edit_page_context(
            request,
            page=page,
            user=user,
            language=language,
            skin=skin,
            wikicode=wikicode,
            edit_notice=edit_notice,
            page_exists=page_exists,
            can_read=can_read,
            can_edit=can_edit,
            revision=revision,
            archived=revision is not None and revision_id is not None,
            error=status == NOT_FOUND,
            form=form
        ), status)
    else:
        wikicode, page_lang = api.get_page_message(page, 'ReadForbidden')
        return (_get_read_page_context(
            request,
            page=page,
            user=user,
            language=language,
            content_language=page_lang or language,
            skin=skin,
            wikicode=wikicode,
            noindex=True,
            page_exists=page_exists,
            can_read=False,
            can_edit=False
        ), FORBIDDEN)


def _get_page_history(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        page_exists: bool,
        can_read: bool,
        can_edit: bool,
        url_params: typ.Dict[str, str]
) -> typ.Tuple[page_context.PageContext, int]:
    if can_read:
        if page_exists:
            revisions = api.get_page_revisions(page, user)
            paginator, paginator_page = api.paginate(user, revisions, url_params)
            return (_get_page_history_context(
                request,
                page=page,
                user=user,
                language=language,
                skin=skin,
                can_read=can_read,
                can_edit=can_edit,
                paginator=paginator,
                paginator_page=paginator_page,
                page_exists=True
            ), FOUND)
        else:
            return (_get_page_history_context(
                request,
                page=page,
                user=user,
                language=language,
                skin=skin,
                can_read=can_read,
                can_edit=can_edit,
                paginator=None,
                paginator_page=0,
                page_exists=False
            ), NOT_FOUND)
    else:
        wikicode, page_lang = api.get_page_message(page, 'ReadForbidden')
        return (_get_read_page_context(
            request,
            page=page,
            user=user,
            language=language,
            content_language=page_lang or language,
            skin=skin,
            wikicode=wikicode,
            noindex=True,
            page_exists=page_exists,
            can_read=False,
            can_edit=False
        ), FORBIDDEN)


def submit_page_content(
        request: dj_wsgi.WSGIRequest,
        namespace_id: int,
        title: str,
        user: models.User,
        wikicode: str,
        comment: str,
        minor: bool,
        language: settings.i18n.Language,
        section_id: int = None,
        hidden_category: bool = False
) -> typ.Tuple[typ.Tuple[page_context.PageContext, int], bool]:
    context = get_page_context(request, namespace_id, title, user, language, user.data.skin,
                               redirect_enabled=False)
    try:
        api.submit_page_content(context, namespace_id, title, user, wikicode, comment, minor, section_id=section_id,
                                hidden_category=hidden_category)
    except api.PageEditForbidden:
        return get_page_context(request, namespace_id, title, user, language, user.data.skin, action=EDIT), False
    except api.PageEditConflit:
        pass  # TODO handle conflicts
    else:
        return get_page_context(request, namespace_id, title, user, language, user.data.skin,
                                redirect_enabled=False), True


def get_bad_title_page(
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        error: typ.Union[api.EmptyPageTitleException, api.BadTitleException],
        request: dj_wsgi.WSGIRequest
) -> page_context.PageContext:
    if isinstance(error, api.EmptyPageTitleException):
        return _get_special_page_context('Empty title', user, language, skin, request)[0]
    elif isinstance(error, api.BadTitleException):
        return _get_special_page_context('Bad title', user, language, skin, request, invalid_char=str(error))[0]
    else:
        raise ValueError('invalid error type')


def _format_message(page_content: str, **kwargs) -> str:
    return string.Template(page_content).safe_substitute(kwargs)


def _get_read_page_context(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        content_language: settings.i18n.Language,
        skin: str,
        wikicode: str,
        noindex: bool,
        page_exists: bool,
        can_read: bool,
        can_edit: bool,
        redirected_from: str = None,
        revision: models.PageRevision = None,
        archived: bool = False,
        raw: bool = False
) -> page_context.PageContext:
    base_context = _get_base_page_context(
        request,
        page=page,
        mode=SPECIAL if page.namespace_id == settings.SPECIAL_NS.id else READ,
        user=user,
        language=language,
        content_language=content_language,
        skin=skin,
        noindex=noindex,
        page_exists=page_exists,
        can_read=can_read,
        can_edit=can_edit
    )

    context = page_context.ReadPageContext(
        base_context,
        wikicode=wikicode,
        revision=revision,
        archived=archived,
        page_categories=api.get_page_categories(page, get_hidden=user.data.display_hidden_categories)
    )

    if not raw:
        if page.content_model == settings.PAGE_TYPE_WIKI:
            render, is_redirect = api.render_wikicode(wikicode, context, no_redirect=True, enable_comment=True)
        else:
            # Custom HTML formatter because default one wraps
            # pre tag inside div and we don???t want that.
            # noinspection PyUnresolvedReferences
            class CodeHtmlFormatter(pyg_format.HtmlFormatter):
                def wrap(self, source, _):
                    return self._wrap_code(source)

                # noinspection PyMethodMayBeStatic
                def _wrap_code(self, source):
                    yield 0, '<pre class="wpy-code-highlight"><code>'
                    for i, t in source:
                        yield i, t
                    yield 0, '</code></pre>'

            lexer_type = {
                settings.PAGE_TYPE_MODULE: 'python3',
                settings.PAGE_TYPE_JAVASCRIPT: 'js',
                settings.PAGE_TYPE_STYLESHEET: 'css',
            }.get(page.content_model)

            if lexer_type is not None:
                render = pygments.highlight(
                    wikicode,
                    pyg_lex.get_lexer_by_name(lexer_type),
                    CodeHtmlFormatter(**{
                        'linenos': 'table',
                        'classprefix': 'wpy-code-highlight-',
                        'cssclass': 'wpy-code-highlight-',
                        'lineseparator': '<br/>',
                    })
                )
            else:
                render = wikicode
            is_redirect = False
        render = dj_safe.mark_safe(render)
    else:
        render = wikicode
        is_redirect = False
    if redirected_from:
        referer = api.extract_namespace_and_title(redirected_from, ns_as_id=True)
    else:
        referer = None

    context.rendered_page_content = render
    context.is_redirection = is_redirect
    context.redirected_from = referer

    return context


def _get_edit_page_context(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        wikicode: str,
        edit_notice: str,
        page_exists: bool,
        can_read: bool,
        can_edit: bool,
        revision: models.PageRevision,
        archived: bool,
        error: bool,
        form: forms.EditPageForm = None
) -> page_context.PageContext:
    base_context = _get_base_page_context(
        request,
        page=page,
        mode=EDIT,
        user=user,
        language=language,
        content_language=language,
        skin=skin,
        noindex=True,
        page_exists=page_exists,
        can_read=can_read,
        can_edit=can_edit
    )

    edit_notice = dj_safe.mark_safe(api.render_wikicode(edit_notice, base_context))
    if error:
        code = ''
        error_notice = dj_safe.mark_safe(api.render_wikicode(wikicode, base_context))
    else:
        code = wikicode
        error_notice = ''
    initial = {
        'content': wikicode,
    }

    if page_exists and page.is_category:
        category_data = api.get_category_metadata(page.title)
        if category_data:
            initial['hidden_category'] = category_data.hidden

    form = form or forms.EditPageForm(
        language=base_context.language,
        disabled=not base_context.user_can_edit,
        warn_unsaved_changes=base_context.user.data.unsaved_changes_warning,
        initial=initial
    )

    return page_context.EditPageContext(
        base_context,
        wikicode=code,
        revision=revision,
        archived=archived,
        edit_notice=edit_notice,
        error_notice=error_notice,
        form=form
    )


def _get_page_history_context(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        user: models.User,
        language: settings.i18n.Language,
        skin: str,
        can_read: bool,
        can_edit: bool,
        paginator,
        paginator_page: int,
        page_exists: bool
) -> page_context.PageContext:
    base_context = _get_base_page_context(
        request,
        page=page,
        mode=HISTORY,
        user=user,
        language=language,
        content_language=language,
        skin=skin,
        noindex=True,
        page_exists=page_exists,
        can_read=can_read,
        can_edit=can_edit
    )
    return page_context.ListPageContext(base_context, paginator=paginator, page=paginator_page)


def _get_base_page_context(
        request: dj_wsgi.WSGIRequest,
        page: models.Page,
        mode: str,
        user: models.User,
        language: settings.i18n.Language,
        content_language: settings.i18n.Language,
        skin: str,
        noindex: bool,
        page_exists: bool,
        can_read: bool,
        can_edit: bool
) -> page_context.PageContext:
    main_page_full_title = api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
    languages = list(sorted(settings.i18n.get_languages().values(), key=lambda l: l.name))
    is_main_page = page.full_title == main_page_full_title
    page_ns_gender = api.get_user_gender_from_page(page.namespace_id, page.title)
    now = api.now()
    user_now = api.now(user.data.timezone_info)

    return page_context.PageContext(
        request=request,
        project_name=settings.PROJECT_NAME,
        main_page_namespace=settings.NAMESPACES[settings.MAIN_PAGE_NAMESPACE_ID],
        main_page_title=settings.MAIN_PAGE_TITLE,
        main_page_title_url=api.as_url_title(settings.MAIN_PAGE_TITLE, escape=True),
        main_page_full_title=main_page_full_title,
        main_page_full_title_url=api.as_url_title(main_page_full_title, escape=True),
        page=page,
        page_namespace_gender=page_ns_gender,
        mode=mode,
        noindex=noindex,
        show_title=not is_main_page or not settings.HIDE_TITLE_ON_MAIN_PAGE or not page_exists or mode != READ,
        user=user,
        skin=skins.get_skin(skin),
        language=language,
        content_language=content_language,
        default_language=settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE),
        languages=languages,
        page_exists=page_exists,
        user_can_read=can_read,
        user_can_edit=can_edit,
        user_can_hide=user.has_right(settings.RIGHT_HIDE_REVISIONS),
        date_time=now,
        user_date_time=user_now,
        date=now.date(),
        user_date=user_now.date(),
        time=now.time(),
        user_time=user_now.time(),
        revisions_list_page_min=settings.REVISIONS_LIST_PAGE_MIN,
        revisions_list_page_max=settings.REVISIONS_LIST_PAGE_MAX,
        rc_min_days=settings.RC_DAYS_MIN,
        rc_max_days=settings.RC_DAYS_MAX,
        rc_min_revisions=settings.RC_REVISIONS_MIN,
        rc_max_revisions=settings.RC_REVISIONS_MAX
    )
