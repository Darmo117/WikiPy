from . import _registry


@_registry.parser_function(name='if')
def _if(cond: str, then: str, else_: str) -> str:
    return then if cond else else_


@_registry.parser_function(name='if_equals')
def _if_equals(value1: str, value2: str, then: str, else_: str) -> str:
    return then if value1 == value2 else else_


@_registry.parser_function(name='if_exists', takes_api=True)
def _if_exists(api, page_title: str, then: str, else_: str) -> str:
    ns_id, title = api.extract_namespace_and_title(page_title)
    return then if api.page_exists(ns_id, title) else else_
