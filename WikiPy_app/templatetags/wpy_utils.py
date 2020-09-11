import typing as typ

import django.template as dj_template

register = dj_template.Library()


@register.filter
def join(values: typ.List[typ.Any], separator: str) -> str:
    return separator.join(map(str, values))
