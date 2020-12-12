import typing as typ

import django.template as dj_template

register = dj_template.Library()


@register.filter
def join(values: typ.List[typ.Any], separator: str) -> str:
    return separator.join(map(str, values))


@register.filter
def replace(value: str, repl: str) -> str:
    old, new = repl.split(',', maxsplit=1)
    return value.replace(old, new)


@register.filter
def get_attr(o: typ.Any, attr_name: str) -> typ.Any:
    return getattr(o, attr_name)
