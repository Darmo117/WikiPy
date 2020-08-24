import collections
import json
import os
import string
import typing as typ

from ..apps import WikiPyAppConfig

_ENTRIES = {}


# TODO load extensions’ translations
def load_translations(base_dir: str):
    global _ENTRIES

    path = os.path.join(base_dir, WikiPyAppConfig.name, 'translations.json')
    with open(path, mode='r', encoding='UTF-8') as _trans_file:
        _ENTRIES = _build_mapping(None, json.load(_trans_file))


def _build_mapping(root: typ.Optional[str], json_object: typ.Mapping[str, typ.Union[str, typ.Mapping]]) \
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
            mapping = dict(mapping, **_build_mapping(key, v))
        else:
            raise ValueError(f'illegal value type "{type(v)}" for translation value')

    return mapping


def trans(key: str, *, none_if_undefined=False, **kwargs) -> typ.Optional[str]:
    value = _ENTRIES.get(key, key if not none_if_undefined else None)
    if value is not None:
        return string.Template(value).safe_substitute(kwargs)
    return None
