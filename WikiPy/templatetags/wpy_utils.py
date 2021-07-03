"""
This module defines usefull template filters.
"""
import pydoc
import typing as typ

import django.template as dj_template

register = dj_template.Library()


@register.filter
def join(values: typ.List[typ.Any], separator: str) -> str:
    """
    Concatenates all values from the given list after converting them to strings.
    Calls the join method on the list.

    :param values: The values to concatenate.
    :param separator: The string to insert between each value.
    :return: The resulting string.
    """
    return separator.join(map(str, values))


@register.filter
def replace(s: str, repl: str) -> str:
    """
    Replaces all occurences of the given value in a string.
    Calls the replace method on the first string.

    :param s: The string to perform the action on.
    :param repl: The old and new values separated by a comma.
    :return: The new string.
    """
    old, new = repl.split(',', maxsplit=1)
    return s.replace(old, new)


@register.filter
def format_string(s: str, v) -> str:
    """
    Formats a string with a single placeholder.
    Calls the format method on the string.

    :param s: The string.
    :param v: The value.
    :return: The formatted string.
    """
    return s.format(v)


@register.filter
def get_attr(o: typ.Any, attr_name: str) -> typ.Any:
    """
    Returns the value of the specified attribute from the object.
    Calls the getattr function.

    :param o: The object.
    :param attr_name: The attribute name.
    :return: The attribute value.
    :raises AttributeError: If the object has no attribute with the specified name.
    """
    return getattr(o, attr_name)


@register.filter
def is_instance(obj, type_name: str) -> bool:
    """
    Checks whether the given object is an instance of the given type name.
    Calls the isinstance function on the object.

    :param obj: The object.
    :param type_name: The full type name.
    :return: True if the object is an instance of the type, False otherwise.
    """
    t = pydoc.locate(type_name)
    if isinstance(t, type):
        return isinstance(obj, t)
    return False


__all__ = [
    'join',
    'replace',
    'format_string',
    'get_attr',
    'is_instance',
]
