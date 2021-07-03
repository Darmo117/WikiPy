"""This module defines classes and functions to load extensions.
Extensions are plugins that add features to the wiki they are installed on.

All extensions have to be installed in this package, each in separate sub-packages.

The extension’s directory should contain a extension.json file that must feature the following attributes:
    - version (string): the extension’s version.
    - build_date (string): the extension’s build date as an ISO date (YYYY-MM-DDTHH:mm:SS).
    - home_url (string): the URL to the page that describes the extension. May be null.
    - license (string): the extension’s license. May be null.
    - fallback_language (string): the code of the language to use
        if there are no mapping for a translation key in a given language.
    - authors (array): the list of people that worked on the extension. Each item should have the following attributes:
        - name: the person’s full name or alias.
        - url: the person’s home page URL. May be null.

Extensions’ packages should have the following structure:
    - langs: a directory that contains language files. Each language file should be named “<language code>.json”.
        Each language file should have these two attributes:
            - name (string): the extension’s name in the language.
            - description (string): the extension’s description in the language.
    - parser (optional): a package that may contain files that register new parser features.
        - functions.py (optional): a file that registers additional parser functions.
        - magic_keywords.py (optional): a file that registers additional parser magic keywords.
    - special_pages (optional): a package that may contain special pages, each file containing a single special page.
    - extension.json: the file described above.
    - models.py (optional): the file that defines all model classes for the extension.
    - LICENSE (optional): the file containing the full license.
"""
import importlib
import json
import logging
import typing as typ

from .. import settings

MODELS_FILE = 'models'
PARSER_FILES_DIR = 'parser'
MAGIC_KEYWORDS_FILE = 'magic_keywords'
PARSER_FUNCTIONS_FILE = 'functions'


# TODO extension dependencies
class Extension(settings.resource_loader.ExternalResource):
    def __init__(self, path: str, ident: str):
        """
        An extension is a plugin that adds new features to the wiki it is installed on.

        :param path: The path to the extension.
        :param ident: The extension’s ID.
        """
        super(Extension, self).__init__(path, 'extension', ident)

    def load_magic_keywords(self):
        """
        Loads magic keywords.
        These keywords have to be defined in a module named 'magic_keywords.py'.
        If the file is not present, it is skipped.
        """
        logging.info(f'Loading magic keywords for extension "{self.id}"…')
        try:
            importlib.import_module(f'.{self.id}.{PARSER_FILES_DIR}.{MAGIC_KEYWORDS_FILE}', package=__name__)
        except ModuleNotFoundError:
            logging.info(f'No "{MAGIC_KEYWORDS_FILE}.py" found, skipped.')
        else:
            logging.info('Magic keywords loaded successfully.')

    def load_parser_functions(self):
        """
        Loads parser functions.
        These functions have to be defined in a module named 'functions.py'.
        If the file is not present, it is skipped.
        """
        logging.info(f'Loading parser functions for extension "{self.id}"…')
        try:
            importlib.import_module(f'.{self.id}.{PARSER_FILES_DIR}.{PARSER_FUNCTIONS_FILE}', package=__name__)
        except ModuleNotFoundError:
            logging.info(f'No "{PARSER_FUNCTIONS_FILE}.py" found, skipped.')
        else:
            logging.info('Parser functions loaded successfully.')

    def register_logs(self, registry):
        """
        Registers logs.
        These log classes have to be defined in a module named 'models.py'
        which must define a function named 'register_logs' that takes the
        registry as a unique parameter.
        If the file is not present, it is skipped.
        """
        logging.info(f'Registering logs for extension "{self.id}"…')
        try:
            models = importlib.import_module(f'.{self.id}.{MODELS_FILE}', package=__name__)
            # noinspection PyUnresolvedReferences
            models.register_logs(registry)
        except ModuleNotFoundError:
            logging.info(f'No "{MODELS_FILE}.py" found, skipped.')
        except (AttributeError, TypeError):
            logging.error('No "register_logs" function found, skipped.')
        else:
            logging.info('Logs registered successfully.')


_extensions = {}


def load_extension(name: str) -> bool:
    """
    Loads the extension with the given name.

    :param name: Name of the extension to load.
    :return: True if the extension has been loaded, false otherwise.
    """
    logging.info(f'Pre-loading extension "{name}"…')
    try:
        module = importlib.import_module('.' + name, package=__name__)
    except ModuleNotFoundError:  # Should never happen
        logging.error(f'Module "{__name__}.{name}" not found, skipping extension.')
        return False

    try:
        extension = Extension(module.__path__[0], ident=name)
    except KeyError as e:
        logging.error(f'Missing key {e}, skipping extension.')
        return False
    except TypeError as e:
        logging.error(f'Type error, skipping extension: {e}.')
        return False
    except json.JSONDecodeError as e:
        logging.error(f'JSON error, skipping extension: {e}.')
        return False

    extension.load_translations()
    _extensions[extension.id] = extension
    logging.info(f'Extension pre-loaded successfully.')
    return True


def get_extension(ident: str) -> typ.Optional[Extension]:
    """
    Returns the extension with the given ID.

    :param ident: Extension’s ID.
    :return: The extension object or None if the ID is undefined.
    """
    return _extensions.get(ident)


def get_loaded_extensions() -> typ.List[Extension]:
    """Returns a list of all loaded extensions, sorted by ID."""
    return sorted(_extensions.values(), key=lambda e: e.name)


__all__ = [
    'Extension',
    'load_extension',
    'get_extension',
    'get_loaded_extensions',
]
