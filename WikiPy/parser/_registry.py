import dataclasses
import re
import traceback
import typing as typ

from .. import extensions

__all__ = [
    'magic_keyword',
    'parser_function',
    'get_registered_magic_keywords',
    'get_registered_functions',
    'ParserFeature',
    'ParserFunction',
    'MagicKeyword',
]

_EXTENSION_ID_REGEX = re.compile(r'/extensions/(\w+)/')
_NAME_REGEX = re.compile(r'^\w+$')

_magic_keywords = {}
_parser_functions = {}


def _get_extension() -> typ.Optional[extensions.Extension]:
    path = traceback.extract_stack()[-4].filename
    if m := _EXTENSION_ID_REGEX.search(path):
        return extensions.get_extension(m.group(1))
    return None


def parser_function(name=None, function=None, takes_api=False):
    if name is None and function is None:
        # @registry.register()
        def aux(f):
            return _register_function(f.__name__, f, takes_api)

        return aux
    elif name is not None and function is None:
        if callable(name):
            # @registry.register
            return _register_function(name.__name__, name, takes_api)
        else:
            # @registry.register('somename') or @registry.register(name='somename')
            def aux(f):
                return _register_function(name, f, takes_api)

            return aux
    elif name is not None and function is not None:
        # @registry.register('somename', somefunc)
        return _register_function(name, function, takes_api)

    raise ValueError(f'Unsupported arguments to parser.register_function: ({name!r}, {function!r})')


def magic_keyword(name=None, function=None, takes_context=False):
    if name is None and function is None:
        # @registry.register()
        def aux(f):
            return _register_magic_keyword(f.__name__, f, takes_context)

        return aux
    elif name is not None and function is None:
        if callable(name):
            # @registry.register
            return _register_magic_keyword(name.__name__, name, takes_context)
        else:
            # @registry.register('somename') or @registry.register(name='somename')
            def aux(f):
                return _register_magic_keyword(name, f, takes_context)

            return aux
    elif name is not None and function is not None:
        # @registry.register('somename', somefunc)
        return _register_magic_keyword(name, function, takes_context)

    raise ValueError(f'Unsupported arguments to parser.register_function: ({name!r}, {function!r})')


@dataclasses.dataclass(frozen=True)
class ParserFeature:
    name: str
    extension: typ.Optional[extensions.Extension]

    def __str__(self):
        return f'{self.name}'


@dataclasses.dataclass(frozen=True)
class ParserFunction(ParserFeature):
    takes_api: bool
    _function: typ.Callable[[typ.Any], str]
    do_not_call_in_templates = True

    def __call__(self, *args, **kwargs) -> str:
        return self._function(*args, **kwargs)


@dataclasses.dataclass(frozen=True)
class MagicKeyword(ParserFeature):
    takes_context: bool
    _function: typ.Callable
    do_not_call_in_templates = True

    def __call__(self, *args, **kwargs) -> str:
        return self._function(*args, **kwargs)


def get_registered_magic_keywords() -> typ.Dict[str, MagicKeyword]:
    return dict(_magic_keywords)


def get_registered_functions() -> typ.Dict[str, ParserFunction]:
    return dict(_parser_functions)


def _register_magic_keyword(name: str, function, takes_context: bool):
    name = name.upper()
    if name in _magic_keywords:
        raise ValueError(f'Duplicate declaration for magic keyword name "{name}"')
    if not re.fullmatch(_NAME_REGEX, name):
        raise ValueError(f'Invalid magic keyword name "{name}"')
    wrapper = MagicKeyword(name=name, extension=_get_extension(), takes_context=takes_context, _function=function)
    _magic_keywords[name] = wrapper
    return wrapper


def _register_function(name: str, function, takes_api: bool):
    if name in _parser_functions:
        raise ValueError(f'Duplicate declaration for function name "{name}"')
    wrapper = ParserFunction(name=name, extension=_get_extension(), takes_api=takes_api, _function=function)
    _parser_functions[name] = wrapper
    return wrapper
