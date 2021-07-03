"""This module defines classes related to resources (skins, extensions, etc.).

The resource’s directory should contain a JSON file that must feature the following attributes:
    - version (string): the resource’s version.
    - build_date (string): the resource’s build date as an ISO date (YYYY-MM-DDTHH:mm:SS).
    - home_url (string): the URL to the page that describes the resource. May be null.
    - license (string): the resource’s license. May be null.
    - fallback_language (string): the code of the language to use
        if there are no mapping for a translation key in a given language.
    - authors (array): the list of people that worked on the resource. Each item should have the following attributes:
        - name: the person’s full name or alias.
        - url: the person’s home page URL. May be null.
This file should be named “<resource type>.json”.
"""
import collections
import datetime
import json
import logging
import os
import typing as typ

from . import _i18n

AuthorTuple = collections.namedtuple('AuthorTuple', ['name', 'url'])
"""This type represent an author of an external resource as a name and a home page URL."""


class ExternalResource:
    def __init__(self, path: str, resource_type: str, ident: str):
        """An external resource is a resource (like a skin or an extension)
        that is loaded during the wiki’s initialization and that can be
        installed at any time during the wiki’s life span.

        The wiki needs to be restarted for a newly installed extension to be loaded.

        :param path: The path to the directory containing the resource’s JSON file.
        :param resource_type: The type of resource. Corresponds to the name of the resource’s JSON file.
        :param ident: Resource’s unique ID.
        """
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
        """Resource’s unique ID."""
        return self._id

    def name(self, language, none_if_undefined: bool = False) -> str:
        """Returns the name of this resource for the given language.
        If no name is available for this language, the fallback language will be used instead.

        :param none_if_undefined: If true and no name exists for neither the given
            language nor fallback language, None is returned instead of the key.
        :param language: The language to use.
        :type language: WikiPy.settings.i18n.Language
        :return: The name.
        """
        key = f'{self._resource_type}.{self._id}.name'
        trans = language.translate(key, none_if_undefined=True)
        if trans is None:
            trans = _i18n.get_language(self._fallback_language_code) \
                .translate(key, none_if_undefined=none_if_undefined)

        return trans

    def description(self, language, none_if_undefined: bool = False) -> str:
        """Returns the description of this resource for the given language.
        If no description is available for this language, the fallback language will be used instead.

        :param none_if_undefined: If true and no description exists for neither the given
            language nor fallback language, None is returned instead of the key.
        :param language: The language.
        :type language: WikiPy.settings.i18n.Language
        :return: The description.
        """
        key = f'{self._resource_type}.{self._id}.description'
        trans = language.translate(key, none_if_undefined=True)
        if trans is None:
            trans = _i18n.get_language(self._fallback_language_code) \
                .translate(key, none_if_undefined=none_if_undefined)

        return trans

    @property
    def version(self) -> str:
        """This resource’s version."""
        return self._version

    @property
    def build_date(self) -> datetime.datetime:
        """This resource’s build date."""
        return self._build_date

    @property
    def license(self) -> str:
        """This resource’s license."""
        return self._license

    @property
    def home_url(self) -> typ.Optional[str]:
        """This resource’s home URL or None if undefined."""
        return self._home_url

    @property
    def authors(self) -> typ.List[AuthorTuple]:
        """This resource’s authors as a list of AuthorTuple objects."""
        return self._authors.copy()

    @property
    def fallback_language_code(self) -> str:
        """This resource’s fallback language code, i.e. the code of the language
        to use if there are no mapping for a translation key in a given language.
        """
        return self._fallback_language_code

    @property
    def resource_type(self) -> str:
        """This resource’s type."""
        return self._resource_type

    def load_translations(self):
        """Loads the translations for this resource.
        This function tries to load translations for all of the wiki’s languages.
        If a language file is not found, it is simply skipped.

        Language files should be located in directory named 'langs' at the root of the resource’s directory.
        Their name should be <language code>.json.
        """
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
