import abc as _abc
import importlib as _importlib
import logging as _logging
import typing as _typ


class Skin(_abc.ABC):
    def __init__(self, name, label):
        self.__name = name
        self.__label = label

    @property
    def name(self):
        return self.__name

    @property
    def label(self):
        return self.__label

    @_abc.abstractmethod
    def render_wikicode(self, parsed_wikicode) -> str:
        """
        Renders the given parsed wikicode.

        :param parsed_wikicode: The parsed wikicode to render.
        :type parsed_wikicode: django_wiki.api.ParsedWikicode
        :return: The parsed wikicode.
        """
        pass


_LOADED_SKINS = {}


def load_skin(name: str):
    try:
        module = _importlib.import_module('._' + name, package=__name__)
        skin = module.load_skin()
        _LOADED_SKINS[skin.name] = skin
    except ModuleNotFoundError:
        _logging.warning(f'unknown skin name "{name}", ignored')


def get_skin(name: str) -> Skin:
    if name in _LOADED_SKINS:
        return _LOADED_SKINS[name]
    return _LOADED_SKINS['default']


def get_loaded_skins_names() -> _typ.List[str]:
    return sorted(_LOADED_SKINS.keys())
