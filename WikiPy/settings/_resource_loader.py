import collections
import datetime
import json
import logging
import os
import typing as typ

from . import _i18n

AuthorTuple = collections.namedtuple('AuthorTuple', ['name', 'url'])


class ExternalResource:
    def __init__(self, path: str, resource_type: str, ident: str):
        self._path = path
        self._resource_type = resource_type
        self._id = ident
        with open(os.path.join(path, resource_type + '.json'), encoding='UTF-8') as f:
            json_obj = json.load(f)
            self._version = str(json_obj['version'])
            self._build_date = datetime.datetime.fromisoformat(json_obj['build_date'])
            self._license = str(json_obj['license'])
            self._home_url = json_obj.get('home_url')
            self._authors = list(map(lambda item: AuthorTuple(name=item['name'], url=item.get('url')),
                                     json_obj['authors']))
            self._fallback_language_code = str(json_obj['fallback_language'])

    @property
    def id(self) -> str:
        return self._id

    def name(self, language, none_if_undefined: bool = False) -> str:
        """
        Returns the name of this resource for the given language.
        If no name is available for this language, the fallback will be used instead.

        :param none_if_undefined: If true and no name exists for neither the given
        language nor fallback language, None is returned instead of the key.
        :param language: The language.
        :type language: WikiPy.settings.i18n.Language
        :return: The name.
        """
        key = f'{self._resource_type}.{self._id}.name'
        trans = language.translate(key, none_if_undefined=True)
        if trans is None:
            trans = _i18n.get_language(self._fallback_language_code).translate(key, none_if_undefined=none_if_undefined)

        return trans

    def description(self, language, none_if_undefined: bool = False) -> str:
        """
        Returns the description of this resource for the given language.
        If no description is available for this language, the fallback will be used instead.

        :param none_if_undefined: If true and no description exists for neither the given
        language nor fallback language, None is returned instead of the key.
        :param language: The language.
        :type language: WikiPy.settings.i18n.Language
        :return: The description.
        """
        key = f'{self._resource_type}.{self._id}.description'
        trans = language.translate(key, none_if_undefined=True)
        if trans is None:
            trans = _i18n.get_language(self._fallback_language_code).translate(key, none_if_undefined=none_if_undefined)

        return trans

    @property
    def version(self) -> str:
        return self._version

    @property
    def build_date(self) -> datetime.datetime:
        return self._build_date

    @property
    def license(self) -> str:
        return self._license

    @property
    def home_url(self) -> typ.Optional[str]:
        return self._home_url

    @property
    def authors(self) -> typ.List[AuthorTuple]:
        return self._authors.copy()

    @property
    def fallback_language_code(self) -> str:
        return self._fallback_language_code

    @property
    def resource_type(self) -> str:
        return self._resource_type

    def load_translations(self):
        logging.info('Loading translations…')

        for lang in _i18n.get_languages().keys():
            try:
                with open(os.path.join(self._path, 'langs', lang + '.json'), encoding='UTF-8') as f:
                    _i18n.load_resource_mappings(self._resource_type, self._id, lang, json.load(f))
            except json.JSONDecodeError as e:
                logging.error(f'JSON error for language "{lang}", skipped: {e}.')
            except FileNotFoundError:
                logging.warning(f'No mappings found for "{lang}", skipped.')

        logging.info('Translations loaded.')


__all__ = [
    'AuthorTuple',
    'ExternalResource',
]
