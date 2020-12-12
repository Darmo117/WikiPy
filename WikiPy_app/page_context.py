from __future__ import annotations

import dataclasses
import datetime
import typing as typ

import django.core.paginator as dj_page
import django.template.context as dj_context

from . import models, settings, forms, skins

TemplateContext = dj_context.RequestContext


@dataclasses.dataclass
class PageContext:
    project_name: str
    main_page_namespace: str
    main_page_title: str
    main_page_title_url: str
    main_page_full_title: str
    main_page_full_title_url: str
    page: models.Page
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
    local_date_time: datetime.datetime

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

    def __init__(self, context: PageContext, /, to: str, anchor: str = None, is_path: bool = False,
                 display: bool = False):
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

    def __init__(self, context: PageContext, /, wikicode: str, revision: typ.Any = None, archived: bool = False):
        self._context = context
        self.wikicode = wikicode
        self.revision = revision
        self.archived = archived


@dataclasses.dataclass(init=False)
class ReadPageContext(RevisionPageContext):
    rendered_page_content: str
    is_redirection: bool
    redirected_from: typ.Optional[typ.Tuple[int, str]]

    def __init__(self, context: PageContext, /, wikicode: str, is_redirection: bool,
                 revision: typ.Optional[object] = None, archived: bool = False, rendered_page_content: str = '',
                 redirected_from: typ.Tuple[int, str] = None):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.rendered_page_content = rendered_page_content
        self.is_redirection = is_redirection
        self.redirected_from = redirected_from


@dataclasses.dataclass(init=False)
class EditPageContext(RevisionPageContext):
    edit_notice: str
    error_notice: str
    edit_form: forms.EditPageForm

    def __init__(self, context: PageContext, /, wikicode: str, form: forms.EditPageForm,
                 revision: typ.Optional[object] = None, archived: bool = False, edit_notice: str = '',
                 error_notice: str = ''):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.edit_form = form
        self.edit_notice = edit_notice
        self.error_notice = error_notice


@dataclasses.dataclass(init=False)
class ListPageContext(PageContext):
    paginator: dj_page.Paginator
    paginator_page: int

    def __init__(self, context: PageContext, /, paginator: dj_page.Paginator, page: int):
        self._context = context
        self.paginator = paginator
        self.paginator_page = page


@dataclasses.dataclass(init=False)
class SetupPageContext(PageContext):
    setup_form: forms.SetupPageForm
    setup_form_global_errors: typ.List[str]

    def __init__(self, context: PageContext, /, form: forms.SetupPageForm, global_errors: typ.List[str] = None):
        self._context = context
        self.setup_form = form
        self.setup_form_global_errors = global_errors
