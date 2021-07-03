"""
This module defines functions to register magic keywords and parser functions.
"""
import dataclasses
import re
import traceback
import typing as typ

from .. import extensions

_EXTENSION_ID_REGEX = re.compile(r'/extensions/(\w+)/')
_NAME_REGEX = re.compile(r'^\w+$')

_magic_keywords = {}
_parser_functions = {}


def _get_extension() -> typ.Optional[extensions.Extension]:
    path = traceback.extract_stack()[-4].filename
    if m := _EXTENSION_ID_REGEX.search(path):
        return extensions.get_extension(m.group(1))
    return None


def parser_function(name=None, function=None):
    """
    Decorator function to register a new parser function.

    There are three ways to use it:
        - @parser_function or @parser_function()
            The decorated function’s name will be used as the parser function’s name.
        - @parser_function('somename')
            The argument will be used as the name of the parser function.
        - parser_function('somename', function)
            When calling this function directly, the first argument is the parser function’s name,
            the second is the actual function.

    :param name: The name of the parser function if called in the second or third way.
        The decorated function if called in the first way without the parentheses. None otherwise.
        The function’s name should only contain letters, digits and underscores.
    :param function: The actual function if called in the third way, None otherwise.
    :return: The wrapper function.
    """
    if name is None and function is None:
        # @parser_function()
        def aux(f):
            return _register_function(f.__name__, f)

        return aux
    elif name is not None and function is None:
        if callable(name):
            # @parser_function
            return _register_function(name.__name__, name)
        else:
            # @parser_function('somename')
            def aux(f):
                return _register_function(name, f)

            return aux
    elif name is not None and function is not None:
        # parser_function('somename', somefunc)
        return _register_function(name, function)

    raise ValueError(f'Unsupported arguments to register_function: ({name!r}, {function!r})')


def magic_keyword(name=None, function=None, *, takes_context: bool = False):
    """
    Decorator function to register a new magic keyword.

    There are three ways to use it:
        - @magic_keyword or @magic_keyword()
            The decorated function’s name will be used as the magic keyword’s name.
        - @magic_keyword('somename')
            The argument will be used as the name of the magic keyword.
        - magic_keyword('somename', function)
            When calling this function directly, the first argument is the magic keyword’s name,
            the second is the actual function.

    :param name: The name of the magic keyword if called in the second or third way.
        The decorated function if called in the first way without the parentheses. None otherwise.
        The magic keyword’s name should only contain letters, digits and underscores.
    :param function: The actual function if called in the third way, None otherwise.
    :param takes_context:
    :return: The wrapper function.
    """
    if name is None and function is None:
        # @magic_keyword()
        def aux(f):
            return _register_magic_keyword(f.__name__, f, takes_context)

        return aux
    elif name is not None and function is None:
        if callable(name):
            # @magic_keyword
            return _register_magic_keyword(name.__name__, name, takes_context)
        else:
            # @magic_keyword('somename')
            def aux(f):
                return _register_magic_keyword(name, f, takes_context)

            return aux
    elif name is not None and function is not None:
        # @magic_keyword('somename', somefunc)
        return _register_magic_keyword(name, function, takes_context)

    raise ValueError(f'Unsupported arguments to register_function: ({name!r}, {function!r})')


@dataclasses.dataclass(frozen=True)
class ParserFeature:
    """
    A parser feature has a name and may have an associated extension (the one that registered it).
    Only built-in features do not have an extension.
    """
    name: str
    extension: typ.Optional[extensions.Extension]

    def __str__(self):
        return f'{self.name}'


@dataclasses.dataclass(frozen=True)
class ParserFunction(ParserFeature):
    """
    Parser functions are functions that can be called from the wikicode.
    They produce a result depending on the value of their arguments.
    """
    _function: typ.Callable[[typ.Any], str]
    do_not_call_in_templates = True

    def __call__(self, *args, **kwargs) -> str:
        return self._function(*args, **kwargs)


@dataclasses.dataclass(frozen=True)
class MagicKeyword(ParserFeature):
    """
    Magic keywords are template-like features that are substituted by the result returned by their inner function.
    """
    takes_context: bool
    _function: typ.Callable
    do_not_call_in_templates = True

    def __call__(self, *args, **kwargs) -> str:
        return self._function(*args, **kwargs)


def get_registered_magic_keywords() -> typ.Dict[str, MagicKeyword]:
    """Returns a dictonary containing all registered magic keywords associated with their name."""
    return dict(_magic_keywords)


def get_registered_functions() -> typ.Dict[str, ParserFunction]:
    """Returns a dictonary containing all registered parser functions associated with their name."""
    return dict(_parser_functions)


def _register_magic_keyword(name: str, function, takes_context: bool) -> MagicKeyword:
    """
    Registers a magic keyword.

    :param name: The keyword’s name.
    :param function: The keyword’s underlying function.
    :param takes_context: If true, the first argument of the function will be the page context.
    :return: The magic keyword.
    :raises ValueError: If a magic keyword with the same name is already registered or the keyword’s name is invalid.
    """
    name = name.upper()
    if name in _magic_keywords:
        raise ValueError(f'Duplicate declaration for magic keyword name "{name}"')
    if not re.fullmatch(_NAME_REGEX, name):
        raise ValueError(f'Invalid magic keyword name "{name}"')
    wrapper = MagicKeyword(name=name, extension=_get_extension(), takes_context=takes_context, _function=function)
    _magic_keywords[name] = wrapper
    return wrapper


def _register_function(name: str, function) -> ParserFunction:
    """
    Registers a parser function.

    :param name: The parser function’s name.
    :param function: The parser function’s underlying function.
    :return: The parser function.
    :raises ValueError: If a function with the same name is already registered or the function’s name is invalid.
    """
    if name in _parser_functions:
        raise ValueError(f'Duplicate declaration for function name "{name}"')
    if not re.fullmatch(_NAME_REGEX, name):
        raise ValueError(f'Invalid function name "{name}"')
    wrapper = ParserFunction(name=name, extension=_get_extension(), _function=function)
    _parser_functions[name] = wrapper
    return wrapper


__all__ = [
    'magic_keyword',
    'parser_function',
    'get_registered_magic_keywords',
    'get_registered_functions',
    'ParserFeature',
    'ParserFunction',
    'MagicKeyword',
]
