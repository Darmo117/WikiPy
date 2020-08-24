from __future__ import annotations

import dataclasses
import typing as typ

import django.core.paginator as dj_page

TemplateContext = typ.Dict[str, typ.Any]


@dataclasses.dataclass
class PageContext:
    """
    :type user: int
    """
    project_name: str
    main_page_namespace: str
    main_page_title: str
    main_page_title_url: str
    main_page_full_title: str
    main_page_full_title_url: str
    page_title: str
    page_title_url: str
    full_page_title: str
    full_page_title_url: str
    namespace_id: int
    canonical_namespace_name: str
    canonical_namespace_name_url: str
    namespace_name: str
    namespace_name_url: str
    mode: str
    noindex: bool
    show_title: bool
    language: str
    writing_direction: str
    user: typ.Any  # FIXME annotate correctly
    skin_name: str
    page_exists: bool
    user_can_read: bool
    user_can_edit: bool
    user_can_hide: bool
    content_type: str

    def __post_init__(self):
        self._context = None

    def __getattr__(self, item):
        if self._context:
            return getattr(self._context, item)
        raise AttributeError(item)


@dataclasses.dataclass(init=False)
class RevisionPageContext(PageContext):
    wikicode: str
    revision: typ.Optional[typ.Any]  # FIXME annotate correctly
    archived: bool

    def __init__(self, context: PageContext, /, wikicode: str, revision: typ.Any = None, archived: bool = False):
        self._context = context
        self.wikicode = wikicode
        self.revision = revision
        self.archived = archived


@dataclasses.dataclass(init=False)
class ReadPageContext(RevisionPageContext):
    rendered_page_content: str

    def __init__(self, context: PageContext, /, wikicode: str, revision: typ.Optional[object] = None,
                 archived: bool = False, rendered_page_content: str = ''):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.rendered_page_content = rendered_page_content


@dataclasses.dataclass(init=False)
class EditPageContext(RevisionPageContext):
    edit_notice: str
    error_notice: str

    def __init__(self, context: PageContext, /, wikicode: str, revision: typ.Optional[object] = None,
                 archived: bool = False, edit_notice: str = '', error_notice: str = ''):
        super().__init__(context, wikicode=wikicode, revision=revision, archived=archived)
        self.edit_notice = edit_notice
        self.error_notice = error_notice


@dataclasses.dataclass(init=False)
class ListPageContext(PageContext):
    paginator: dj_page.Paginator
    page: int

    def __init__(self, context: PageContext, /, paginator: dj_page.Paginator, page: int):
        self._context = context
        self.paginator = paginator
        self.page = page


@dataclasses.dataclass(init=False)
class SetupPageContext(PageContext):
    setup_invalid_username: bool
    setup_invalid_password: bool
    setup_invalid_email: bool
    setup_invalid_secret_key: bool
    setup_username: typ.Optional[str]
    setup_email: typ.Optional[str]

    def __init__(self, context: PageContext, /, setup_invalid_username: bool, setup_invalid_password: bool,
                 setup_invalid_email: bool, setup_invalid_secret_key: bool, setup_username: str = None,
                 setup_email: str = None):
        self._context = context
        self.setup_invalid_username = setup_invalid_username
        self.setup_invalid_password = setup_invalid_password
        self.setup_invalid_email = setup_invalid_email
        self.setup_invalid_secret_key = setup_invalid_secret_key
        self.setup_username = setup_username
        self.setup_email = setup_email
