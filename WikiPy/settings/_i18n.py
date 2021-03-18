import collections
import dataclasses
import datetime
import json
import logging
import os
import re
import string
import typing as typ

from .. import apps

__all__ = [
    'Language',
    'load_languages',
    'get_language',
    'get_languages',
    'load_resource_mappings',
]


@dataclasses.dataclass(frozen=True)
class Language:
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
        return self.month_names[index - 1][0]

    def get_month_abbreviation(self, index: int) -> str:
        return self.month_names[index - 1][1]

    def get_day_name(self, index: int) -> str:
        return self.day_names[index - 1][0]

    def get_day_abbreviation(self, index: int) -> str:
        return self.day_names[index - 1][1]

    def translate(self, key: str, *, none_if_undefined=False, plural_number: int = None, **kwargs) -> typ.Optional[str]:
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
        return dict(self._js_mappings)


_LANGUAGES: typ.Dict[str, Language] = {}


def load_languages(base_dir: str):
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
    return _LANGUAGES.get(code)


def get_languages() -> typ.Dict[str, Language]:
    return dict(_LANGUAGES)


def load_resource_mappings(resource_type: str, ident: str, lang_code: str,
                           mappings: typ.Mapping[str, typ.Union[str, typ.Mapping]]):
    if lang := get_language(lang_code):
        for k, v in _build_mapping(mappings).items():
            # noinspection PyProtectedMember
            lang._mappings[f'{resource_type}.{ident}.{k}'] = v
        logging.info(f'Mappings for {resource_type} "{ident}" in language "{lang_code}" successfully loaded.')


def _check_datetime_formats(formats: typ.Sequence[str], lang_code: str):
    for dt_format in formats:
        try:
            if '%' not in dt_format:
                raise ValueError(f'no % in format for language "{lang_code}"')
            datetime.datetime.now().strftime(dt_format)
        except ValueError:
            raise ValueError(f'invalid format string "{dt_format}" for language "{lang_code}"')
    if len(formats) == 0:
        raise ValueError(f'no datetime formats defined for language "{lang_code}"')


def _check_month_names(names: typ.Sequence, lang_code: str):
    if len(names) != 12:
        raise ValueError(f'invalid number of month name entries ({len(names)}) for language "{lang_code}"')
    for e in names:
        if len(e) != 2:
            raise ValueError(f'invalid month name entry for language "{lang_code}"')


def _check_day_names(names: typ.Sequence, lang_code: str):
    if len(names) != 7:
        raise ValueError(f'invalid number of day name entries ({len(names)}) for language "{lang_code}"')
    for e in names:
        if len(e) != 2:
            raise ValueError(f'invalid day name entry for language "{lang_code}"')


def _build_mapping(json_object: typ.Mapping[str, typ.Union[str, typ.Mapping]], root: str = None) \
        -> typ.Dict[str, str]:
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
