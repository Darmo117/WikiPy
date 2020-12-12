import abc
import dataclasses
import importlib
import os
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
from django.conf import settings as dj_settings

from .. import apps, page_context, settings, forms, util

MAINTENANCE_CAT = 'maintenance'
PAGE_LISTS_CAT = 'page_lists'
CONNECTION_CAT = 'connection'
USERS_AND_RIGHTS_CAT = 'users_and_rights'
JOURNALS_CAT = 'journals'
DATA_AND_TOOLS_CAT = 'data_and_tools'
REDIRECTIONS_CAT = 'redirections'
VERY_USED_PAGES_CAT = 'very_used_pages'
PAGE_TOOLS_CAT = 'page_tools'
MISC_CAT = 'misc'

CATEGORIES = (
    MAINTENANCE_CAT,
    PAGE_LISTS_CAT,
    CONNECTION_CAT,
    USERS_AND_RIGHTS_CAT,
    JOURNALS_CAT,
    DATA_AND_TOOLS_CAT,
    REDIRECTIONS_CAT,
    VERY_USED_PAGES_CAT,
    PAGE_TOOLS_CAT,
    MISC_CAT,
)


@dataclasses.dataclass(init=False)
class SpecialPageContext(page_context.PageContext):
    display_title: str
    special_page_id: str
    special_page_title: str
    url_special_page_title: str
    canonical_special_page_title: str
    url_canonical_special_page_title: str
    load_special_page_js: bool
    load_special_page_css: bool
    load_special_page_form: bool
    category: typ.Optional[str]
    required_rights: typ.Sequence[str]

    def __init__(self, context: page_context.PageContext, /, display_title: str, special_page_id: str,
                 special_page_title: str, url_special_page_title: str, canonical_special_page_title: str,
                 url_canonical_special_page_title: str, load_special_page_js: bool, load_special_page_css: bool,
                 load_special_page_form: bool, category: str, required_rights: typ.Sequence[str]):
        self._context = context
        self.display_title = display_title
        self.special_page_id = special_page_id
        self.special_page_title = special_page_title
        self.url_special_page_title = url_special_page_title
        self.canonical_special_page_title = canonical_special_page_title
        self.url_canonical_special_page_title = url_canonical_special_page_title
        self.load_special_page_js = load_special_page_js
        self.load_special_page_css = load_special_page_css
        self.load_special_page_form = load_special_page_form
        self.category = category
        self.required_rights = required_rights

    @property
    def user_can_edit(self):
        return False


@dataclasses.dataclass(init=False)
class ReturnToPageContext(page_context.PageContext):
    return_to: str
    return_to_path: bool

    def __init__(self, context: page_context.PageContext, /, to: str, is_path: bool = False):
        self._context = context
        self.return_to = to
        self.return_to_path = is_path


class SpecialPage(abc.ABC):
    def __init__(self, page_id: str, title: str, category: str = None, has_js: bool = False, has_css: bool = False,
                 has_form: bool = False, icon: str = None, access_key: str = None,
                 requires_rights: typ.Sequence[str] = None):
        self.__id = page_id
        self.__title = title
        self.__local_title = settings.SPECIAL_PAGES_LOCAL_NAMES.get(self.__id)
        if category and category not in CATEGORIES:
            raise ValueError(f'invalid special page category "{category}" for page "{page_id}"')
        self.__category = category
        self.__has_js = has_js
        self.__has_css = has_css
        self.__has_form = has_form
        self.__icon = icon
        self.__access_key = access_key
        self.__requires_rights = tuple(requires_rights) if requires_rights else ()

    @property
    def id(self) -> str:
        return self.__id

    @property
    def title(self) -> str:
        return self.__title

    @property
    def local_title(self) -> str:
        return self.__local_title or self.__title

    def display_title(self, language: settings.i18n.Language) -> str:
        return language.translate(f'special.{self.__id}.display_title', none_if_undefined=True) \
               or self.local_title

    @property
    def category(self) -> typ.Optional[str]:
        return self.__category

    @property
    def requires_rights(self) -> typ.Tuple[str]:
        return self.__requires_rights

    @property
    def has_js(self) -> bool:
        return self.__has_js

    @property
    def has_css(self) -> bool:
        return self.__has_css

    @property
    def has_form(self) -> bool:
        return self.__has_form

    @property
    def icon(self) -> typ.Optional[str]:
        return self.__icon

    @property
    def access_key(self) -> typ.Optional[str]:
        return self.__access_key

    def get_title(self, local: bool = True) -> str:
        if local and self.local_title is not None:
            return self.local_title
        else:
            return self.__title

    def matches_title(self, title: str) -> bool:
        title = title.lower()
        return self.__title.lower() == title or self.__local_title is not None and self.__local_title.lower() == title

    def get_data(self, sub_title: str, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest,
                 **kwargs) -> page_context.PageContext:
        """
        Returns the context data needed to render this special page.
        :param sub_title: The string after the first / in the page title.
        :param base_context: The base page context.
        :param request: The HTTP request object.
        :return: The context object. May contain the following entries:
        * display_title (string): The title to display.
        * redirect (string): The page title to redirect the user to.
        * paginator (Paginator): A paginator object (only if a sequence of values were returned by the page).
        * page (int): The page index for the paginator object.
        """
        from .. import api

        sub_title_values = sub_title.split('/')
        if sub_title_values == ['']:
            sub_title_values = []

        special_context = SpecialPageContext(
            base_context,
            display_title=self.display_title(base_context.language),
            special_page_id=self.id,
            special_page_title=self.get_title(local=True),
            url_special_page_title=api.as_url_title(self.get_title(local=True)),
            canonical_special_page_title=self.get_title(local=False),
            url_canonical_special_page_title=api.as_url_title(self.get_title(local=False)),
            load_special_page_js=self.has_js,
            load_special_page_css=self.has_css,
            load_special_page_form=self.has_form,
            category=self.category,
            required_rights=self.requires_rights
        )

        if not self.requires_rights or all([base_context.user.has_right(right) for right in self.requires_rights]):
            context, values, custom_title = self._get_data_impl(sub_title_values, special_context, request, **kwargs)
            if custom_title:
                special_context.display_title = custom_title

            if values:
                paginator, page = api.paginate(values, request.GET)
                context = page_context.ListPageContext(context, paginator=paginator, page=page)
        else:
            context = special_context
            context.user_can_read = False

        return context

    @abc.abstractmethod
    def _get_data_impl(self, sub_title: typ.List[str], base_context: page_context.PageContext,
                       request: dj_wsgi.WSGIRequest, **kwargs) \
            -> typ.Tuple[page_context.PageContext, typ.Iterable[typ.Any], typ.Optional[str]]:
        """
        Returns all necessary data for the render.

        :param api: The API module.
        :param sub_title: The list of values after the first / in the page title.
        :param request: The HTTP request object.
        :return: A tuple containing the context object, an sequence of values (may be empty)
        and an optional title to display in place of the default one.
        """
        pass

    @staticmethod
    def _get_action(request: dj_wsgi.WSGIRequest) -> typ.Optional[str]:
        return util.get_param(request.GET, 'action')

    @staticmethod
    def _get_return_to_context(request: dj_wsgi.WSGIRequest, base_context: page_context.PageContext) \
            -> ReturnToPageContext:
        return_to = util.get_param(request.GET, 'return_to')
        return_to_path = util.get_param(request.GET, 'is_path', default=False, expected_type=bool)
        return ReturnToPageContext(base_context, to=return_to, is_path=return_to_path)

    @staticmethod
    def _get_return_to_path(form: forms.SupportsReturnTo, default_path: str = None) -> typ.Tuple[str, bool]:
        return_to = form.cleaned_data['return_to'] or default_path
        is_path = bool(form.cleaned_data['return_to_path'])
        return return_to, is_path


_SPECIAL_PAGES: typ.Dict[str, SpecialPage] = {}


# TODO load extensions’ special pages
# TODO look out for duplicate titles
def load_special_pages():
    titles = set()
    files = os.listdir(os.path.join(dj_settings.BASE_DIR, apps.WikiPyAppConfig.name, 'special_pages'))
    for filename in filter(lambda fn: not fn.startswith('__') and fn.endswith('.py'), files):
        module = importlib.import_module('.' + filename[:-3], package=__name__)
        # noinspection PyUnresolvedReferences
        sp: SpecialPage = module.load_special_page()
        if sp.get_title(local=False) in titles or sp.get_title(local=True) in titles:
            raise ValueError(f'duplicate special page title for ID "{sp.id}"')
        _SPECIAL_PAGES[sp.id] = sp


def get_special_page(title: str) -> typ.Optional[SpecialPage]:
    for special_page in _SPECIAL_PAGES.values():
        if special_page.matches_title(title):
            return special_page
    return None


def get_special_page_for_id(page_id: str) -> typ.Optional[SpecialPage]:
    return _SPECIAL_PAGES.get(page_id)


def get_special_pages() -> typ.Tuple[SpecialPage]:
    return tuple(_SPECIAL_PAGES.values())


__all__ = [
    'SpecialPageContext',
    'ReturnToPageContext',
    'SpecialPage',
    'load_special_pages',
    'get_special_page',
    'get_special_page_for_id'
]
