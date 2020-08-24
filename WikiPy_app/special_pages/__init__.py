import abc as _abc
import dataclasses
import importlib as _importlib
import os as _os
import typing as _typ

from .. import apps as _apps, page_context as _page_context


@dataclasses.dataclass(init=False)
class SpecialPageContext(_page_context.PageContext):
    display_title: str
    special_page_id: str
    special_page_title: str
    url_special_page_title: str
    canonical_special_page_title: str
    url_canonical_special_page_title: str
    load_special_page_js: bool
    load_special_page_css: bool

    def __init__(self, context: _page_context.PageContext, /, display_title: str, special_page_id: str,
                 special_page_title: str, url_special_page_title: str, canonical_special_page_title: str,
                 url_canonical_special_page_title: str, load_special_page_js: bool, load_special_page_css: bool):
        self._context = context
        self.display_title = display_title
        self.special_page_id = special_page_id
        self.special_page_title = special_page_title
        self.url_special_page_title = url_special_page_title
        self.canonical_special_page_title = canonical_special_page_title
        self.url_canonical_special_page_title = url_canonical_special_page_title
        self.load_special_page_js = load_special_page_js
        self.load_special_page_css = load_special_page_css

    @property
    def user_can_edit(self):
        return False


@dataclasses.dataclass(init=False)
class RedirectPageContext(_page_context.PageContext):
    redirect: str

    def __init__(self, context: _page_context.PageContext, /, to: str):
        self._context = context
        self.redirect = to


@dataclasses.dataclass(init=False)
class ReturnToPageContext(_page_context.PageContext):
    return_to: str

    def __init__(self, context: _page_context.PageContext, /, to: str):
        self._context = context
        self.return_to = to


class SpecialPage(_abc.ABC):
    def __init__(self, settings, page_id: str, title: str, has_js: bool = False, has_css: bool = False):
        self.__id = page_id
        self.__title = title
        self.__local_title = settings.i18n.trans(f'special.{self.__id}.title', none_if_undefined=True) or self.__title
        self.__display_title = (settings.i18n.trans(f'special.{self.__id}.display_title', none_if_undefined=True)
                                or self.__local_title)
        self._settings = settings
        self.__has_js = has_js
        self.__has_css = has_css

    @property
    def id(self) -> str:
        return self.__id

    @property
    def title(self) -> str:
        return self.__title

    @property
    def local_title(self) -> _typ.Optional[str]:
        return self.__local_title

    @property
    def display_title(self) -> _typ.Optional[str]:
        return self.__display_title

    @property
    def has_js(self):
        return self.__has_js

    @property
    def has_css(self):
        return self.__has_css

    def get_title(self, local: bool = True) -> str:
        if local and self.__local_title is not None:
            return self.__local_title
        else:
            return self.__title

    def matches_title(self, title: str) -> bool:
        title = title.lower()
        return self.__title.lower() == title or self.__local_title is not None and self.__local_title.lower() == title

    def get_data(self, api, sub_title: str, base_context: _page_context.PageContext, request, **kwargs) \
            -> _page_context.PageContext:
        """
        Returns the context data needed to render this special page.
        :param api: The API module.
        :param sub_title: The string after the first / in the page title.
        :param base_context: The base page context.
        :param request: The HTTP request object.
        :return: The context object. May contain the following entries:
        * display_title (string): The title to display.
        * redirect (string): The page title to redirect the user to.
        * paginator (Paginator): A paginator object (only if a sequence of values were returned by the page).
        * page (int): The page index for the paginator object.
        """
        sub_title_values = sub_title.split('/')
        if sub_title_values == ['']:
            sub_title_values = []

        special_context = SpecialPageContext(
            base_context,
            display_title=self.display_title or self.get_title(),
            special_page_id=self.id,
            special_page_title=self.get_title(local=True),
            url_special_page_title=api.as_url_title(self.get_title(local=True)),
            canonical_special_page_title=self.get_title(local=False),
            url_canonical_special_page_title=api.as_url_title(self.get_title(local=False)),
            load_special_page_js=self.has_js,
            load_special_page_css=self.has_css
        )

        context, values, custom_title = self._get_data_impl(api, sub_title_values, special_context, request, **kwargs)
        if custom_title:
            special_context.display_title = custom_title

        if values:
            paginator, page = api.paginate(values, request.GET)
            context = _page_context.ListPageContext(context, paginator=paginator, page=page)

        return context

    @_abc.abstractmethod
    def _get_data_impl(self, api, sub_title: _typ.List[str], base_context: _page_context.PageContext,
                       request, **kwargs) \
            -> _typ.Tuple[_page_context.PageContext, _typ.Iterable[_typ.Any], _typ.Optional[str]]:
        """
        Returns all necessary data for the render.

        :param api: The API module.
        :param sub_title: The list of values after the first / in the page title.
        :param request: The HTTP request object.
        :return: A tuple containing the context object, an sequence of values (may be empty)
        and an optional title to display in place of the default one.
        """
        pass


_SPECIAL_PAGES: _typ.Dict[str, SpecialPage] = {}


# TODO load extensions’ special pages
# TODO look out for duplicate titles
def load_special_pages(base_dir: str, settings):
    titles = set()
    files = _os.listdir(_os.path.join(base_dir, _apps.WikiPyAppConfig.name, 'special_pages'))
    for filename in filter(lambda fn: not fn.startswith('__') and fn.endswith('.py'), files):
        module = _importlib.import_module('.' + filename[:-3], package=__name__)
        # noinspection PyUnresolvedReferences
        sp: SpecialPage = module.load_special_page(settings)
        if sp.get_title(local=False) in titles or sp.get_title(local=True) in titles:
            raise ValueError(f'duplicate special page title for ID "{sp.id}"')
        _SPECIAL_PAGES[sp.id] = sp


def get_special_page(title: str) -> _typ.Optional[SpecialPage]:
    for special_page in _SPECIAL_PAGES.values():
        if special_page.matches_title(title):
            return special_page
    return None


def get_special_page_for_id(page_id: str) -> _typ.Optional[SpecialPage]:
    return _SPECIAL_PAGES.get(page_id)
