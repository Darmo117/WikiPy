import abc as _abc
import importlib as _importlib
import os as _os
import typing as _typ

from .. import apps as _apps


class SpecialPage(_abc.ABC):
    def __init__(self, settings, page_id: str, title: str):
        self.__id = page_id
        self.__title = title
        self.__local_title = settings.i18n.trans(f'special.{self.__id}.title', none_if_undefined=True) or self.__title
        self.__display_title = (settings.i18n.trans(f'special.{self.__id}.display_title', none_if_undefined=True)
                                or self.__local_title)
        self._settings = settings

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

    def get_title(self, local: bool = True) -> str:
        if local and self.__local_title is not None:
            return self.__local_title
        else:
            return self.__title

    def matches_title(self, title: str) -> bool:
        title = title.lower()
        return self.__title.lower() == title or self.__local_title is not None and self.__local_title.lower() == title

    def get_data(self, api, sub_title: str, request) -> _typ.Dict[str, _typ.Any]:
        data, values, custom_title = self._get_data_impl(api, sub_title, request)
        context = {
            **data,
            'display_title': custom_title or self.display_title or self.get_title(),
        }

        if values:
            paginator, page = api.paginate(values, request.GET)
            context = {
                **context,
                'paginator': paginator,
                'page': page,
            }

        return context

    @_abc.abstractmethod
    def _get_data_impl(self, api, sub_title: str, request) \
            -> _typ.Tuple[_typ.Dict[str, _typ.Any], _typ.Iterable[_typ.Any], _typ.Optional[str]]:
        pass


_SPECIAL_PAGES: _typ.Dict[str, SpecialPage] = {}


# TODO load extensions’ special pages
# TODO look out for duplicate titles
def load_special_pages(base_dir: str, settings):
    files = _os.listdir(_os.path.join(base_dir, _apps.WikiPyAppConfig.name, 'special_pages'))
    for filename in filter(lambda fn: not fn.startswith('__') and fn.endswith('.py'), files):
        module = _importlib.import_module('.' + filename[:-3], package=__name__)
        # noinspection PyUnresolvedReferences
        sp = module.load_special_page(settings)
        _SPECIAL_PAGES[sp.id] = sp


def get_special_page(title: str) -> _typ.Optional[SpecialPage]:
    for special_page in _SPECIAL_PAGES.values():
        if special_page.matches_title(title):
            return special_page
    return None


def get_special_page_for_id(page_id: str) -> _typ.Optional[SpecialPage]:
    return _SPECIAL_PAGES.get(page_id)
