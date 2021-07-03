"""
This module defines the default parser functions.
"""
from . import _registry


@_registry.parser_function('if')
def _if(cond: str, then: str, else_: str) -> str:
    return then if cond else else_


@_registry.parser_function
def if_equals(value1: str, value2: str, then: str, else_: str) -> str:
    return then if value1 == value2 else else_


@_registry.parser_function
def if_exists(page_title: str, then: str, else_: str) -> str:
    from ..api import titles as api_titles, pages as api_pages

    ns_id, title = api_titles.extract_namespace_and_title(page_title)
    return then if api_pages.page_exists(ns_id, title) else else_


@_registry.parser_function
def expr(expression: str) -> str:
    return expression  # TODO
