from __future__ import annotations

import dataclasses
import datetime
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.core.paginator as dj_page
import django.template.context as dj_context

from . import models, settings, forms, skins

TemplateContext = dj_context.RequestContext


@dataclasses.dataclass
class PageContext:
    request: dj_wsgi.WSGIRequest
    project_name: str
    main_page_namespace: settings.Namespace
    main_page_title: str
    main_page_title_url: str
    main_page_full_title: str
    main_page_full_title_url: str
    page: models.Page
    page_namespace_gender: typ.Optional[models.Gender]
    suppages: typ.List[models.Page]
    mode: str
    noindex: bool
    show_title: bool
    user: models.User
    skin: skins.Skin
    default_language: settings.i18n.Language
    language: settings.i18n.Language
    content_language: settings.i18n.Language
    languages: typ.List[settings.i18n.Language]
    page_exists: bool
    user_can_read: bool
    user_can_edit: bool
    user_can_hide: bool
    date_time: datetime.datetime
    user_date_time: datetime.datetime
    date: datetime.date
    user_date: datetime.date
    time: datetime.time
    user_time: datetime.time
    revisions_list_page_min: int
    revisions_list_page_max: int
    rc_min_days: int
    rc_max_days: int
    rc_min_revisions: int
    rc_max_revisions: int

    def __post_init__(self):
        self._context = None

    def __getattr__(self, item):
        if self._context:
            return getattr(self._context, item)
        raise AttributeError(item)


@dataclasses.dataclass(init=False)
class RedirectPageContext(PageContext):
    redirect: str
    redirect_anchor: typ.Optional[str]
    is_path: bool
    display_redirect: bool

    def __init__(
            self,
            context: PageContext,
            /,
            to: str,
            anchor: str = None,
            is_path: bool = False,
            display: bool = False
    ):
        self._context = context
        self.redirect = to
        self.redirect_anchor = anchor
        self.is_path = is_path
        self.display_redirect = display


@dataclasses.dataclass(init=False)
class RevisionPageContext(PageContext):
    wikicode: str
    revision: typ.Optional[models.PageRevision]
    archived: bool

    def __init__(
            self,
            context: PageContext,
            /,
            wikicode: str,
            revision: typ.Any = None,
            archived: bool = False
    ):
        self._context = context
        self.wikicode = wikicode
        self.revision = revision
        self.archived = archived


@dataclasses.dataclass(init=False)
class ReadPageContext(RevisionPageContext):
    rendered_page_content: str
    is_redirection: bool
    redirected_from: typ.Optional[typ.Tuple[int, str]]
    page_categories: typ.List[typ.Tuple[models.Page, models.CategoryData]]

    def __init__(
            self,
            context: PageContext,
            /,
            wikicode: str = None,
            is_redirection: bool = None,
            revision: typ.Optional[object] = None,
            archived: bool = False,
            rendered_page_content: str = '',
            redirected_from: typ.Tuple[int, str] = None,
            page_categories: typ.List[typ.Tuple[models.Page, models.CategoryData]] = None
    ):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.rendered_page_content = rendered_page_content
        self.is_redirection = is_redirection
        self.redirected_from = redirected_from
        self.page_categories = page_categories


@dataclasses.dataclass(init=False)
class TalkPageContext(PageContext):
    user_can_edit_talk: bool
    rendered_page_content: typ.Optional[str]
    is_redirection: bool
    redirected_from: typ.Optional[typ.Tuple[int, str]]
    edit_protection_status: typ.Optional[models.PageProtectionStatus]
    edit_protection_log_entry: typ.Optional[models.PageProtectionLogEntry]
    new_topic_form: forms.NewTopicForm
    new_topic_form_global_errors: typ.List[str]
    edit_message_form: forms.EditMessageForm
    edit_message_form_global_errors: typ.List[str]

    def __init__(
            self,
            context: PageContext,
            /,
            can_edit_talk: bool,
            new_topic_form: forms.NewTopicForm,
            edit_message_form: forms.EditMessageForm,
            new_topic_form_global_errors: typ.List[str] = None,
            edit_message_form_global_errors: typ.List[str] = None,
            rendered_page_content: str = None,
            is_redirection: bool = None,
            redirected_from: typ.Tuple[int, str] = None,
            protection_status: models.PageProtectionStatus = None,
            protection_log_entry: models.PageProtectionLogEntry = None
    ):
        self._context = context
        self.user_can_edit_talk = can_edit_talk
        self.new_topic_form = new_topic_form
        self.edit_message_form = edit_message_form
        self.new_topic_form_global_errors = new_topic_form_global_errors
        self.edit_message_form_global_errors = edit_message_form_global_errors
        self.rendered_page_content = rendered_page_content
        self.is_redirection = is_redirection
        self.redirected_from = redirected_from
        self.edit_protection_status = protection_status
        self.edit_protection_log_entry = protection_log_entry


@dataclasses.dataclass(init=False)
class EditPageContext(RevisionPageContext):
    edit_notice: str
    error_notice: str
    edit_form: forms.EditPageForm
    edit_show_interface_warning: bool
    edit_protection_status: typ.Optional[models.PageProtectionStatus]
    edit_protection_log_entry: typ.Optional[models.PageProtectionLogEntry]

    def __init__(
            self,
            context: PageContext,
            /,
            wikicode: str,
            form: forms.EditPageForm,
            revision: typ.Optional[object] = None,
            archived: bool = False,
            edit_notice: str = '',
            error_notice: str = '',
            show_interface_warning: bool = False,
            protection_status: models.PageProtectionStatus = None,
            protection_log_entry: models.PageProtectionLogEntry = None
    ):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.edit_form = form
        self.edit_notice = edit_notice
        self.error_notice = error_notice
        self.edit_show_interface_warning = show_interface_warning
        self.edit_protection_status = protection_status
        self.edit_protection_log_entry = protection_log_entry


@dataclasses.dataclass(init=False)
class ListPageContext(PageContext):
    paginator: dj_page.Paginator
    paginator_page: int

    def __init__(self, context: PageContext, /, paginator: dj_page.Paginator, page: int):
        self._context = context
        self.paginator = paginator
        self.paginator_page = page


@dataclasses.dataclass(init=False)
class CategoryPageContext(ListPageContext):
    subcategories: typ.Sequence[typ.Tuple[models.Page, str]]

    def __init__(
            self,
            context: PageContext,
            /,
            paginator: dj_page.Paginator,
            page: int,
            subcategories: typ.Sequence[typ.Tuple[models.Page, str]]
    ):
        super().__init__(context, paginator, page)
        self.subcategories = subcategories


@dataclasses.dataclass(init=False)
class SetupPageContext(PageContext):
    setup_form: forms.SetupPageForm
    setup_form_global_errors: typ.List[str]

    def __init__(self, context: PageContext, /, form: forms.SetupPageForm, global_errors: typ.List[str] = None):
        self._context = context
        self.setup_form = form
        self.setup_form_global_errors = global_errors
