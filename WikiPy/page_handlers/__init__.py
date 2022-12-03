"""
This module defines handler classes for the different page actions.
"""
from __future__ import annotations

import abc
import string
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.utils.safestring as dj_safe
import pygments
import pygments.formatters as pyg_format
import pygments.lexers as pyg_lex

from .. import settings, models, special_pages, page_context, skins, forms, setup
from ..api import pages as api_pages, users as api_users, titles as api_titles, datetime as api_dt, errors as api_errors

STATUS_FOUND = 200
STATUS_FORBIDDEN = 403
STATUS_NOT_FOUND = 404

ACTION_READ = 'read'
ACTION_TALK = 'talk'
ACTION_SUBMIT_MESSAGE = 'submit_message'
ACTION_EDIT = 'edit'
ACTION_SUBMIT = 'submit'
ACTION_HISTORY = 'history'
ACTION_RAW = 'raw'

MODE_READ = 'read'
MODE_TALK = 'talk'
MODE_EDIT = 'edit'
MODE_HISTORY = 'history'
MODE_SPECIAL = 'special'
MODE_SETUP = 'setup'


class ActionHandler(abc.ABC):
    """
    Base action handler class.
    Calling the constructor of this class returns the concrete class for the given action.
    """

    @staticmethod
    def valid_actions() -> typ.Iterable[str]:
        """Returns the list of valid page actions."""
        return ActionHandler.__handlers().keys()

    def __new__(cls, **kwargs):
        action = kwargs['action']

        if kwargs['namespace_id'] == settings.SPECIAL_NS.id:
            if kwargs['title'] == settings.WIKI_SETUP_PAGE_TITLE:
                actual_class = _SetupActionHandler
            else:
                actual_class = _ReadActionHandler
        else:
            actual_class = ActionHandler.__handlers().get(action)

        if not actual_class:
            raise ValueError(f'Invalid action "{action}"')

        return super().__new__(actual_class)

    def __init__(
            self,
            action: str,
            request: dj_wsgi.WSGIRequest,
            namespace_id: int,
            title: str,
            user: models.User,
            language: settings.i18n.Language,
            skin_id: str,
            revision_id: int = None,
            redirect_enabled: bool = True,
            redirects_list: typ.List[str] = None,
            special_page_kwargs: typ.Dict[str, typ.Any] = None
    ):
        """
        Creates a handler for the given action.

        :param action: The action.
        :param request: The HTTP request.
        :param namespace_id: Requested page’s namespace ID.
        :param title: Requested page’s title.
        :param user: User performing the action.
        :param language: Language to display the page in.
        :param skin_id: Skin to use when rendering the page.
        :param revision_id: Page’s revision ID. May be ignored for some actions.
        :param redirect_enabled: If true and the page is a redirection,
            the resulting context will be for the target page, not the requested page.
        :param redirects_list: The list of all redirects until this point. Used to detect redirection loops.
        :param special_page_kwargs: If the requested page is special, these arguments will be passed onto it.
        """
        self._action = action
        self._request = request
        self._page, self._page_exists = api_pages.get_page(namespace_id, title)
        if not self._page_exists:
            self._page.content_model = api_pages.get_default_content_model(namespace_id, title)
        self._can_edit, self._can_edit_talk = user.can_edit_page(namespace_id, title)
        self._can_read = user.can_read_page(namespace_id, title)
        self._user = user
        self._language = language
        self._skin = skins.get_skin(skin_id)
        self._revision_id = revision_id
        self._redirect_enabled = redirect_enabled
        self._redirects_list = redirects_list
        self._method = request.method
        self._get = request.GET
        self._post = request.POST
        self._special_page_kwargs = special_page_kwargs or {}

        # Fields that should be defined by subclasses in get_page_context()
        self._mode: str = MODE_READ
        # noinspection PyTypeChecker
        self._content_language: settings.i18n.Language = None
        self._wikicode: str = ''
        self._noindex: bool = False
        # noinspection PyTypeChecker
        self._redirected_from: str = None
        # noinspection PyTypeChecker
        self._revision: models.PageRevision = None

    @abc.abstractmethod
    def get_page_context(self) -> typ.Tuple[page_context.PageContext, int]:
        """
        Returns the context for the requested page and action.

        :return: A tuple containing the context and an error code.
        """
        pass

    @property
    def archived_revision(self) -> bool:
        """Whether the user requested a specific page revision ID."""
        return self._revision is not None and self._revision_id is not None

    def _get_read_page_context(self) -> page_context.PageContext:
        """Returns the read page context."""
        base_context = self._get_base_page_context()

        context = page_context.ReadPageContext(
            base_context,
            wikicode=self._wikicode,
            revision=self._revision,
            archived=self.archived_revision,
            page_categories=api_pages.get_page_categories(
                self._page.namespace_id,
                self._page.title,
                get_maintenance=self._user.data.display_maintenance_categories
            )
        )

        if self._action != ACTION_RAW:
            if self._page.content_model == settings.PAGE_TYPE_WIKI:
                render, is_redirect = api_pages.render_wikicode(self._wikicode, context, no_redirect=True,
                                                                enable_comment=True)
            else:
                # Custom HTML formatter because default one wraps
                # pre tag inside div and we don’t want that.
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
                }.get(self._page.content_model)

                if lexer_type is not None:
                    render = pygments.highlight(
                        self._wikicode,
                        pyg_lex.get_lexer_by_name(lexer_type),
                        CodeHtmlFormatter(**{
                            'linenos': 'table',
                            'classprefix': 'wpy-code-highlight-',
                            'cssclass': 'wpy-code-highlight-',
                            'lineseparator': '<br/>',
                        })
                    )
                else:
                    render = self._wikicode
                is_redirect = False
            render = dj_safe.mark_safe(render)

            if self._page.namespace_id == settings.CATEGORY_NS.id:
                pages = api_pages.get_pages_in_category(self._page.title)
                paginator, page = api_pages.paginate(self._user, pages, self._get)
                context = page_context.CategoryPageContext(
                    context,
                    paginator=paginator,
                    page=page,
                    subcategories=api_pages.get_subcategories(self._page.title)
                )
        else:
            render = self._wikicode
            is_redirect = False
        if self._redirected_from:
            referer = api_titles.extract_namespace_and_title(self._redirected_from, ns_as_id=True)
        else:
            referer = None

        context.rendered_page_content = render
        context.is_redirection = is_redirect
        context.redirected_from = referer

        return context

    def _get_base_page_context(self) -> page_context.PageContext:
        """Returns the base page context."""
        main_page_full_title = api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
        languages = list(sorted(settings.i18n.get_languages().values(), key=lambda l: l.name))
        is_main_page = self._page.full_title == main_page_full_title
        page_ns_gender = api_users.get_user_gender_from_page(self._page.namespace_id, self._page.title)
        now = api_dt.now()
        user_now = api_dt.now(self._user.data.timezone_info)
        suppages = api_pages.get_suppages(self._page.namespace_id, self._page.title)

        return page_context.PageContext(
            request=self._request,
            project_name=settings.PROJECT_NAME,
            main_page_namespace=settings.NAMESPACES[settings.MAIN_PAGE_NAMESPACE_ID],
            main_page_title=settings.MAIN_PAGE_TITLE,
            main_page_title_url=api_titles.as_url_title(settings.MAIN_PAGE_TITLE, escape=True),
            main_page_full_title=main_page_full_title,
            main_page_full_title_url=api_titles.as_url_title(main_page_full_title, escape=True),
            page=self._page,
            page_namespace_gender=page_ns_gender,
            suppages=suppages,
            mode=self._mode,
            noindex=self._noindex,
            show_title=(not is_main_page or not settings.HIDE_TITLE_ON_MAIN_PAGE or
                        not self._page_exists or self._mode != MODE_READ),
            user=self._user,
            skin=self._skin,
            language=self._language,
            content_language=self._content_language,
            default_language=settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE),
            languages=languages,
            page_exists=self._page_exists,
            user_can_read=self._can_read,
            user_can_edit=self._can_edit,
            user_can_hide=self._user.has_right(settings.RIGHT_DELETE_REVISIONS),
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

    @staticmethod
    def __handlers() -> typ.Dict[str, ActionHandler]:
        """A dictionary mapping every action to a concrete handler class."""
        # Cannot use a class property as subclasses would not yet be defined
        # noinspection PyTypeChecker
        return {
            ACTION_READ: _ReadActionHandler,
            ACTION_TALK: _TalkActionHandler,
            ACTION_SUBMIT_MESSAGE: _TalkActionHandler,
            ACTION_EDIT: _EditActionHandler,
            ACTION_SUBMIT: _EditActionHandler,
            ACTION_HISTORY: _HistoryActionHandler,
            ACTION_RAW: _ReadActionHandler,
        }

    @staticmethod
    def _format_message(s: str, **kwargs) -> str:
        """
        $-formats a string with the given values.

        :param s: The string to format.
        :param kwargs: The values to insert.
        :return: The formatted string.
        """
        return string.Template(s).safe_substitute(kwargs)


class _ReadActionHandler(ActionHandler):
    """'read' action handler."""

    def get_page_context(self):
        if self._page.namespace_id == settings.SPECIAL_NS.id and self._page_exists:
            base_title = api_titles.get_special_page_title(self._page.title)
            sub_title = api_titles.get_special_page_sub_title(self._page.title)
            special_page = special_pages.get_special_page(base_title)
            self._mode = MODE_SPECIAL
            self._noindex = True
            base_context = self._get_base_page_context()
            context = special_page.get_data(sub_title, base_context, self._request, **self._special_page_kwargs)
            return context, STATUS_FOUND

        redirect = None
        redirect_anchor = None
        display_redirect = False
        revision = None

        if not self._page_exists:
            status = STATUS_NOT_FOUND
            if self._page.namespace_id == settings.SPECIAL_NS.id:
                wikicode, page_lang = api_pages.get_message('NoSpecialPage', performer=self._user)
            else:
                wikicode, page_lang = api_pages.get_message('NoPage', performer=self._user)

        elif not self._can_read:
            status = STATUS_FORBIDDEN
            wikicode, page_lang = api_pages.get_message('ReadForbidden', performer=self._user)

        else:
            status = STATUS_FOUND
            page_lang = None
            wikicode = ''
            try:
                revision = api_pages.get_page_revision(self._page.namespace_id, self._page.title,
                                                       performer=self._user, revision_id=self._revision_id)
                if not revision:
                    redirect = self._page.full_title
                elif self._revision_id is None:
                    wikicode = revision.content
                    page_lang = self._page.content_language
                    if redir := api_pages.get_redirect(wikicode):
                        display_redirect = True
                        redirect, redirect_anchor = redir
                        if redirect in (self._redirects_list or []):
                            self._redirect_enabled = False
            except api_errors.RevisionDoesNotExistError:
                wikicode, page_lang = api_pages.get_message('InvalidRevisionID', performer=self._user)
                wikicode = self._format_message(wikicode, revision_id=self._revision_id)

        self._content_language = page_lang or self._language
        self._wikicode = wikicode
        self._noindex = status != STATUS_FOUND or self._revision_id is not None
        self._revision = revision
        self._redirected_from = self._redirects_list[0] if self._redirects_list else None
        self._mode = MODE_SPECIAL if self._page.namespace_id == settings.SPECIAL_NS.id else MODE_READ
        context = self._get_read_page_context()

        if not redirect or not self._redirect_enabled:
            return context, status
        else:
            return page_context.RedirectPageContext(context, redirect, anchor=redirect_anchor,
                                                    display=display_redirect), STATUS_FOUND


class _TalkActionHandler(ActionHandler):
    """'talk' action handler."""

    def get_page_context(self):
        redirect = None
        redirect_anchor = None
        display_redirect = False

        if self._can_read:
            render = None
            status = STATUS_FOUND
            self._mode = MODE_TALK
            self._content_language = self._language
            self._noindex = True
            self._redirected_from = self._redirects_list[0] if self._redirects_list else None
            base_context = self._get_base_page_context()
            # Display redirection if necessary
            if revision := api_pages.get_page_revision(self._page.namespace_id, self._page.title, performer=self._user):
                if redir := api_pages.get_redirect(revision.content):
                    display_redirect = True
                    redirect, redirect_anchor = redir
                    if redirect in (self._redirects_list or []):
                        self._redirect_enabled = False
                        render = dj_safe.mark_safe(api_pages.render_wikicode(
                            revision.content,
                            base_context,
                            no_redirect=True,
                            enable_comment=False
                        )[0])

            if not render and self._can_edit_talk and self._action == ACTION_SUBMIT_MESSAGE:
                pass

            warn_unsaved = base_context.user.data.unsaved_changes_warning
            new_topic_form = forms.NewTopicForm(
                language=base_context.language,
                warn_unsaved_changes=warn_unsaved
            )
            edit_message_form = forms.EditMessageForm(
                language=base_context.language,
                warn_unsaved_changes=warn_unsaved
            )

            protection_status, log_entry = None, None
            if prot_status := api_pages.get_page_protection(base_context.page.namespace_id, base_context.page.title):
                if prot_status[0].applies_to_talk_page:
                    protection_status, log_entry = prot_status

            context = page_context.TalkPageContext(
                base_context,
                can_edit_talk=self._can_edit_talk,
                new_topic_form=new_topic_form,
                edit_message_form=edit_message_form,
                rendered_page_content=render,
                is_redirection=redirect is not None,
                redirected_from=self._redirected_from,
                protection_status=protection_status,
                protection_log_entry=log_entry
            )

        else:
            self._mode = MODE_READ
            status = STATUS_FORBIDDEN
            self._wikicode, _ = api_pages.get_message('ReadForbidden', performer=self._user)
            context = self._get_read_page_context()

        if not redirect or not self._redirect_enabled:
            return context, status
        else:
            return page_context.RedirectPageContext(context, redirect, anchor=redirect_anchor,
                                                    display=display_redirect), STATUS_FOUND


class _EditActionHandler(ActionHandler):
    """'edit' action handler."""

    def get_page_context(self):
        if self._can_edit or self._can_read:
            if not self._can_edit and not self._page_exists:
                self._wikicode, page_lang = api_pages.get_page_message(
                    self._page.namespace_id, self._page.title, 'CreateForbidden', performer=self._user,
                    no_per_title_notice=True)
                self._content_language = page_lang or self._language
                self._noindex = True
                self._mode = MODE_READ
                return self._get_read_page_context(), STATUS_FORBIDDEN

            if self._can_edit:
                edit_notice = api_pages.get_page_message(self._page.namespace_id, self._page.title, 'EditNotice',
                                                         performer=self._user)[0]
            else:
                # TODO prendre en compte les blocages
                edit_notice = api_pages.get_page_message(self._page.namespace_id, self._page.title, 'EditForbidden',
                                                         performer=self._user)[0]

            try:
                revision = api_pages.get_page_revision(self._page.namespace_id, self._page.title,
                                                       performer=self._user, revision_id=self._revision_id)
                if revision:
                    wikicode = revision.content
                else:
                    wikicode = ''
                status = STATUS_FOUND
            except api_errors.RevisionDoesNotExistError:
                message, _ = api_pages.get_message('InvalidRevisionID', performer=self._user)
                if message:
                    wikicode = self._format_message(message, revision_id=self._revision_id)
                else:
                    wikicode = ''
                revision = None
                status = STATUS_NOT_FOUND

            self._wikicode = wikicode
            self._revision = revision

            if self._action == ACTION_SUBMIT:
                form = forms.EditPageForm(self._post, warn_unsaved_changes=self._user.data.unsaved_changes_warning)
                if form.is_valid():
                    self._wikicode = form.cleaned_data['content']
                    section_id = form.cleaned_data['section_id']
                    if section_id:
                        try:
                            section_id = int(section_id)
                        except ValueError:
                            section_id = None
                    else:
                        section_id = None
                    comment = form.cleaned_data['comment']
                    minor = form.cleaned_data['minor_edit']
                    # noinspection PyUnusedLocal
                    follow_page = form.cleaned_data['follow_page']  # TODO
                    maintenance_category = form.cleaned_data['maintenance_category']
                    success = self._submit_page_content(
                        comment,
                        minor,
                        section_id=section_id,
                        maintenance_category=maintenance_category
                    )
                    if success:
                        # Prevent redirection from reading mode if new wikicode is a redirection rule
                        self._request.session['no_redirect'] = True
                        return page_context.RedirectPageContext(
                            self._get_base_page_context(),
                            to=self._page.full_title
                        ), STATUS_FOUND
            else:
                form = forms.EditPageForm(
                    language=self._get_base_page_context().language,
                    initial={
                        'content': self._wikicode,
                    }
                )

            return (self._get_edit_page_context(
                edit_notice=edit_notice,
                page_exists=self._page_exists,
                error=status == STATUS_NOT_FOUND,
                form=form
            ), status)

        else:
            self._wikicode, page_lang = api_pages.get_page_message(self._page.namespace_id, self._page.title,
                                                                   'ReadForbidden', performer=self._user)
            self._content_language = page_lang or self._language
            self._noindex = True
            self._mode = MODE_READ
            return self._get_read_page_context(), STATUS_FORBIDDEN

    def _submit_page_content(self, comment: str, minor: bool, section_id: int = None,
                             maintenance_category: bool = False) \
            -> bool:
        self._redirect_enabled = False
        self._mode = MODE_READ
        context = self._get_read_page_context()
        try:
            ns_id = self._page.namespace_id
            title = self._page.title
            current_revision_id = api_pages.get_page_revision(ns_id, title, performer=self._user)
            api_pages.submit_page_content(context, ns_id, title, self._wikicode, comment, minor,
                                          section_id=section_id, maintenance_category=maintenance_category,
                                          current_revision_id=current_revision_id, performer=context.user)
        except api_errors.PageEditForbiddenError:
            return False
        except api_errors.PageEditConflictError:
            # TODO handle conflicts
            return False
        else:
            return True

    def _get_edit_page_context(self, edit_notice: str, page_exists: bool, error: bool,
                               form: forms.EditPageForm = None) -> page_context.PageContext:
        self._mode = MODE_EDIT
        self._noindex = True
        base_context = self._get_base_page_context()

        edit_notice = dj_safe.mark_safe(api_pages.render_wikicode(edit_notice, base_context))
        if error:
            self._wikicode = ''
            error_notice = dj_safe.mark_safe(api_pages.render_wikicode(self._wikicode, base_context))
        else:
            error_notice = ''
        initial = {
            'content': self._wikicode,
        }

        if page_exists and self._page.is_category:
            category_data = api_pages.get_category_metadata(self._page.title)
            if category_data:
                initial['maintenance_category'] = category_data.maintenance

        status = api_pages.get_page_protection(base_context.page.namespace_id, base_context.page.title)

        if status:
            protection_status, log_entry = status
        else:
            protection_status, log_entry = None, None

        form = form or forms.EditPageForm(
            language=base_context.language,
            disabled=not base_context.user_can_edit,
            warn_unsaved_changes=base_context.user.data.unsaved_changes_warning,
            initial=initial
        )

        return page_context.EditPageContext(
            base_context,
            wikicode=self._wikicode,
            revision=self._revision,
            archived=self.archived_revision,
            edit_notice=edit_notice,
            error_notice=error_notice,
            show_interface_warning=self._page.namespace_id in (settings.WIKIPY_NS.id, settings.GADGET_NS.id),
            protection_status=protection_status,
            protection_log_entry=log_entry,
            form=form
        )


class _HistoryActionHandler(ActionHandler):
    """'history' action handler."""

    def get_page_context(self):
        self._noindex = True
        if self._can_read:
            if self._page_exists:
                revisions = api_pages.get_page_revisions(self._page, performer=self._user)
                paginator, paginator_page = api_pages.paginate(self._user, revisions, self._get)
                return self._get_page_history_context(paginator=paginator, paginator_page=paginator_page), STATUS_FOUND
            else:
                return self._get_page_history_context(paginator=None, paginator_page=0), STATUS_NOT_FOUND
        else:
            self._wikicode, page_lang = api_pages.get_page_message(self._page.namespace_id, self._page.title,
                                                                   'ReadForbidden', performer=self._user)
            self._content_language = page_lang or self._language
            self._mode = MODE_READ
            return self._get_read_page_context(), STATUS_FORBIDDEN

    def _get_page_history_context(self, paginator, paginator_page: int) -> page_context.PageContext:
        self._mode = MODE_HISTORY
        base_context = self._get_base_page_context()
        return page_context.ListPageContext(base_context, paginator=paginator, page=paginator_page)


class _SetupActionHandler(ActionHandler):
    """'setup' action handler."""

    def get_page_context(self):
        if not setup.are_pages_setup():
            if self._method == 'POST':
                form = forms.SetupPageForm(self._post)
                errors = []
                is_valid = form.is_valid()
                if is_valid:
                    if form.passwords_match():
                        username = form.cleaned_data['username']
                        password = form.cleaned_data['password']
                        email = form.cleaned_data['email']
                        secret_key = form.cleaned_data['secret_key']
                        status = setup.setup(self._request, username, password, email, secret_key)

                        if status == setup.SUCCESS:
                            setup.delete_key_file()
                        else:
                            errors.append(status)
                    else:
                        errors.append('passwords_mismatch')

                if errors or not is_valid:
                    return self._get_setup_page_context(form, errors)
            else:
                setup.generate_secret_key_file()
                return self._get_setup_page_context(forms.SetupPageForm())

        return page_context.RedirectPageContext(
            self._get_base_page_context(),
            to=api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
        ), STATUS_FORBIDDEN

    def _get_setup_page_context(self, form: forms.SetupPageForm, errors: typ.List[str] = None):
        self._mode = MODE_SETUP
        self._page_exists = True
        context = self._get_base_page_context()
        return page_context.SetupPageContext(context, form=form, global_errors=errors), STATUS_FOUND
