"""
This module defines classes and functions related to I18N.
"""
import collections
import dataclasses
import datetime
import json
import logging
import os
import pathlib
import re
import string
import typing as typ

from .. import apps

ILLEGAL_PLACEHOLDERS = 'cxX'


@dataclasses.dataclass(frozen=True)
class Language:
    """
    This class represents a language.
    Each language is defined by single JSON file located in the “translations” directory.

    Datetime format placeholders %c, %x and %X will be rejected.
    """
    code: str
    name: str
    writing_direction: str
    main_namespace_name: str
    default_datetime_format_id: int
    datetime_formats: typ.Tuple[str]
    month_names: typ.Tuple[typ.Tuple[str, str]]
    day_names: typ.Tuple[typ.Tuple[str, str]]
    _mappings: typ.Dict[str, str]
    _js_mappings: typ.Dict[str, str]

    _ops = {
        '<': (lambda v1, v2: v1 < v2),
        '>': (lambda v1, v2: v1 > v2),
        '<=': (lambda v1, v2: v1 <= v2),
        '>=': (lambda v1, v2: v1 >= v2),
        '=': (lambda v1, v2: v1 == v2),
        '!=': (lambda v1, v2: v1 != v2),
    }

    def get_month_name(self, index: int) -> str:
        """
        Returns the name of the month for the given index.
        January is 1.

        :param index: Month index, from 1 to 12.
        :return: The month’s name.
        """
        return self.month_names[index - 1][0]

    def get_month_abbreviation(self, index: int) -> str:
        """
        Returns the abbreviated name of the month for the given index.
        January is 1.

        :param index: Month index, from 1 to 12.
        :return: The month’s abbreviated name.
        """
        return self.month_names[index - 1][1]

    def get_day_name(self, index: int) -> str:
        """
        Returns the name of the week day for the given index.
        Monday is 1.

        :param index: Week day index, from 1 to 7.
        :return: The week day’s name.
        """
        return self.day_names[index - 1][0]

    def get_day_abbreviation(self, index: int) -> str:
        """
        Returns the abbreviated name of the week day for the given index.
        Monday is 1.

        :param index: Week day index, from 1 to 7.
        :return: The week day’s abbreviated name.
        """
        return self.day_names[index - 1][1]

    def translate(self, key: str, *, none_if_undefined=False, plural_number: int = None, **kwargs) -> typ.Optional[str]:
        """
        Returns the translation for a given key.

        :param key: The key to translated.
        :param none_if_undefined: If true, None will be returned instead of the key if no mapping for it was found.
        :param plural_number: The number of entities designated by the pluralized string.
            Useful for languages that have dual, trial, quadral, paucal, etc. number categories.
        :param kwargs: Additonal arguments used to format the translated string.
        :return: The translated string or the key/None if no mapping was found.
        """
        if plural_number is not None:
            for k in filter(lambda k_: k_.startswith(key), self._mappings.keys()):
                condition = k[k.rindex('.') + 1:]
                if condition == '':
                    template_string = self._mappings[k]
                    break
                elif m := re.fullmatch(r'([<>]=?|!?=)(\d+)', condition):
                    if self._ops[m[1]](plural_number, int(m[2])):
                        template_string = self._mappings[k]
                        break
            else:
                template_string = None
        else:
            template_string = self._mappings.get(key, key if not none_if_undefined else None)

        if template_string is not None:
            return string.Template(template_string).safe_substitute(kwargs)

        return None

    @property
    def javascript_mappings(self) -> typ.Dict[str, str]:
        """Returns the JavaScript mappings for this language."""
        return dict(self._js_mappings)


_LANGUAGES: typ.Dict[str, Language] = {}


def load_languages(base_dir: pathlib.Path):
    """
    Loads all languages defined in the “translations” directory.

    :param base_dir: The site’s root directory.
    """
    global _LANGUAGES

    trans_dir = os.path.join(base_dir, apps.WikiPyConfig.name, 'translations')
    for file_name in filter(lambda fname: fname[0] != '_' and fname.endswith('.json'), os.listdir(trans_dir)):
        with open(os.path.join(trans_dir, file_name), mode='r', encoding='UTF-8') as f:
            json_obj = json.load(f)
        lang_name = str(json_obj['name'])
        lang_code = str(json_obj['code'])
        writing_direction = str(json_obj['writing_direction'])
        main_ns = str(json_obj['main_namespace_name'])
        defaut_format = int(json_obj['default_datetime_format'])
        formats = list(map(str, json_obj['datetime_formats']))
        _check_datetime_formats(formats, lang_code)
        # noinspection PyTypeChecker
        months: typ.Tuple[typ.Tuple[str, str], ...] = \
            tuple(tuple(map(str, name)) for name in json_obj['month_names'])
        _check_month_names(months, lang_code)
        # noinspection PyTypeChecker
        days: typ.Tuple[typ.Tuple[str, str], ...] = \
            tuple(tuple(map(str, name)) for name in json_obj['day_names'])
        _check_day_names(days, lang_code)
        mappings = _build_mapping(json_obj['mappings'])
        js_mappings = {k[len('javascript.'):]: v for k, v in mappings.items() if k.startswith('javascript.')}

        _LANGUAGES[lang_code] = Language(
            code=lang_code,
            name=lang_name,
            writing_direction=writing_direction,
            main_namespace_name=main_ns,
            default_datetime_format_id=defaut_format,
            datetime_formats=tuple(formats),
            month_names=months,
            day_names=days,
            _mappings=mappings,
            _js_mappings=js_mappings
        )


def get_language(code: str) -> typ.Optional[Language]:
    """
    Returns the language for the given code.

    :param code: The language code.
    :return: The language or None if the code is undefined.
    """
    return _LANGUAGES.get(code)


def get_languages() -> typ.Dict[str, Language]:
    """Returns a dictionary mapping each language code to its Language instance."""
    return dict(_LANGUAGES)


def load_resource_mappings(resource_type: str, ident: str, lang_code: str,
                           mappings: typ.Mapping[str, typ.Union[str, typ.Mapping]]):
    """
    Loads the mappings for the given language after it has been loaded.
    This function is used to load translations defined by extensions.
    If the language code is undefined, this function does nothing.

    :param resource_type: The type of resource that loaded these mappings.
    :param ident: The ID of the resource.
    :param lang_code: The code of the language to add mappings to.
    :param mappings: The mappings to add.
    """
    if lang := get_language(lang_code):
        for k, v in _build_mapping(mappings).items():
            # noinspection PyProtectedMember
            lang._mappings[f'{resource_type}.{ident}.{k}'] = v
        logging.info(f'Mappings for {resource_type} "{ident}" in language "{lang_code}" successfully loaded.')


def check_datetime_format(dt_format: str):
    """
    Checks the date formats when loading languages.
    All placeholders used by strftime() are accepted except %c, %x and %X.

    :param dt_format: Date formats to check.
    :raises ValueError: If the format string doesn’t contain any placeholder or has an invalid one.
    """
    if '%' not in dt_format:
        raise ValueError(f'no placeholders found in format string"')

    for placeholder in ILLEGAL_PLACEHOLDERS:
        p = '%' + placeholder
        if p in dt_format:
            raise ValueError(
                f'illegal placeholder {p} found in format string "{dt_format}"')

    try:
        # Attempt to format a dummy date to check if the format is valid.
        datetime.datetime.now().strftime(dt_format)
    except ValueError:
        raise ValueError(f'invalid format string "{dt_format}"')


def _check_datetime_formats(formats: typ.Sequence[str], lang_code: str):
    """
    Checks the date formats when loading languages.
    Placeholders %c, %x and %X will be rejected.

    :param formats: Date formats to check.
    :param lang_code: The language code.
    :raises ValueError: If the list is empty or any of the items either
        doesn’t contain any placeholder or has an invalid one.
    """
    for dt_format in formats:
        try:
            check_datetime_format(dt_format)
        except ValueError as e:
            raise ValueError(str(e) + f' for language "{lang_code}"')
    if len(formats) == 0:
        raise ValueError(f'no datetime formats defined for language "{lang_code}"')


def _check_month_names(names: typ.Sequence, lang_code: str):
    """
    Checks the months names when loading languages.

    :param names: Months names to check.
    :param lang_code: The language code.
    :raises ValueError: If there are not exactly 12 values in the list or not all items are tuples with 2 values.
    """
    if len(names) != 12:
        raise ValueError(f'invalid number of month name entries ({len(names)}) for language "{lang_code}"')
    for e in names:
        if len(e) != 2:
            raise ValueError(f'invalid month name entry for language "{lang_code}"')


def _check_day_names(names: typ.Sequence, lang_code: str):
    """
    Checks the week days names when loading languages.

    :param names: Days names to check.
    :param lang_code: The language code.
    :raises ValueError: If there are not exactly 7 values in the list or not all items are tuples with 2 values.
    """
    if len(names) != 7:
        raise ValueError(f'invalid number of day name entries ({len(names)}) for language "{lang_code}"')
    for e in names:
        if len(e) != 2:
            raise ValueError(f'invalid day name entry for language "{lang_code}"')


def _build_mapping(json_object: typ.Mapping[str, typ.Union[str, typ.Mapping]], root: str = None) \
        -> typ.Dict[str, str]:
    """
    Converts a JSON object to a flat key-value mapping.
    This function is recursive.

    :param json_object: The JSON object to flatten.
    :param root: The root to prepend to the keys.
    :return: The flattened mapping.
    :raises ValueError: If one of the values in the JSON object is neither a string or a mapping.
    """
    mapping = {}

    for k, v in json_object.items():
        if root is not None:
            key = f'{root}.{k}'
        else:
            key = k
        if isinstance(v, str):
            mapping[key] = str(v)
        elif isinstance(v, collections.Mapping):
            mapping = dict(mapping, **_build_mapping(v, key))
        else:
            raise ValueError(f'illegal value type "{type(v)}" for translation value')

    return mapping


__all__ = [
    'Language',
    'load_languages',
    'get_language',
    'get_languages',
    'load_resource_mappings',
]
