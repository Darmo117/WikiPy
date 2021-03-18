import typing as typ

from django.http import request as dj_request

T = typ.TypeVar('T')


def add_entries(query_dict: dj_request.QueryDict, **entries) -> dj_request.QueryDict:
    new_dict = query_dict.copy()
    for k, v in entries.items():
        if isinstance(v, typ.List):
            new_dict.setlist(k, v)
        else:
            new_dict[k] = v
    return new_dict


def get_param(query_dict: typ.Union[dj_request.QueryDict, typ.Dict[str, typ.Any]], param_name: str, *,
              is_list: bool = False, expected_type: typ.Callable[[str], T] = str, default: T = None) -> T:
    try:
        if not is_list:
            value = query_dict.get(param_name, default)
            if value == '':
                return default
            return expected_type(value) if value is not None else None
        else:
            values = query_dict.getlist(param_name, default)
            if values:
                return list(map(expected_type, values))
            return values
    except ValueError:
        return default


__all__ = [
    'add_entries',
    'get_param',
]
