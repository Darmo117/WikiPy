import importlib
import json
import logging
import typing as typ

from .. import settings

__all__ = [
    'Extension',
    'load_extension',
    'get_extension',
    'get_loaded_extensions',
]

PARSER_FILES_DIR = 'parser'
MAGIC_KEYWORDS_FILE = 'magic_keywords'
PARSER_FUNCTIONS_FILE = 'functions'


class Extension(settings.resource_loader.ExternalResource):
    def __init__(self, path: str, ident: str):
        super(Extension, self).__init__(path, 'extension', ident)

    def load_magic_keywords(self):
        logging.info(f'Loading magic keywords for extension "{self.id}"…')
        try:
            importlib.import_module(f'.{self.id}.{PARSER_FILES_DIR}.{MAGIC_KEYWORDS_FILE}', package=__name__)
        except ModuleNotFoundError:
            logging.info(f'No "{MAGIC_KEYWORDS_FILE}.py" found, skipped.')
        else:
            logging.info(f'Magic keywords loaded successfully.')

    def load_parser_functions(self):
        logging.info(f'Loading parser functions for extension "{self.id}"…')
        try:
            importlib.import_module(f'.{self.id}.{PARSER_FILES_DIR}.{PARSER_FUNCTIONS_FILE}', package=__name__)
        except ModuleNotFoundError:
            logging.info(f'No "{PARSER_FUNCTIONS_FILE}.py" found, skipped.')
        else:
            logging.info(f'Parser functions loaded successfully.')


_extensions = {}


def load_extension(name: str) -> bool:
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


def get_extension(name: str) -> typ.Optional[Extension]:
    return _extensions.get(name)


def get_loaded_extensions() -> typ.List[Extension]:
    return sorted(_extensions.values(), key=lambda e: e.name)
