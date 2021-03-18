import abc
import re
import typing as typ
import urllib.parse as url_parse

import django.conf as dj_conf

from . import _nodes


class Tag(abc.ABC):
    def __init__(self, name: str, auto_recursive: bool):
        self.__name = name
        self.__auto_recursive = auto_recursive

    @property
    def name(self) -> str:
        return self.__name

    @property
    def auto_recursive(self) -> bool:
        return self.__auto_recursive

    @abc.abstractmethod
    def parse_wikicode(self, wikicode: str) -> _nodes.WikicodeNode:
        """
        Parses the given wikicode.

        :param wikicode: The wikicode to parse.
        :return: A node.
        """
        pass


#############
# HTML tags #
#############


class ExtendedHTMLTag(Tag, abc.ABC):
    def __init__(self, name: str, inline: bool, auto_recursive: bool, *attributes: str):
        super().__init__(name, auto_recursive)
        self.__name = name
        self.__inline = inline
        self.__attributes = attributes

    @property
    def inline(self) -> bool:
        return self.__inline

    @property
    def attributes(self) -> typ.Tuple[str]:
        return self.__attributes


#################
# Non-HTML tags #
#################


class NonHTMLTag(Tag, abc.ABC):
    """This type of tag that cannot be defined through extensions."""

    def __init__(self, name: str, open_delimiter: str, close_delimiter: str, multiline: bool, auto_recursive: bool):
        r"""Defines a non-HTML tag. This type of tag has opening and closing delimiters.

        :param name: Tag’s internal name.
        :param open_delimiter: Opening delimiter, must be exactly 2 characters long.
        :param close_delimiter: Closing delimiter, must be exactly 2 characters long.
        :param multiline: If true, the tag can span multiple lines; otherwise the parsing will stop at the first \n.
        :param auto_recursive: If true, the tag can contain itself; otherwise internal occurences will not be parsed.
        """
        super().__init__(name, auto_recursive)
        self.__open_delimiter = open_delimiter
        self.__close_delimiter = close_delimiter
        self.__multiline = multiline

    @property
    def open_delimiter(self) -> str:
        return self.__open_delimiter

    @property
    def close_delimiter(self) -> str:
        return self.__close_delimiter

    @property
    def multiline(self) -> bool:
        return self.__multiline


class InternalLinkOrCategoryTag(NonHTMLTag):
    def __init__(self):
        super().__init__('internal_link', '[[', ']]', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        parts = list(map(str.strip, wikicode.split('|', maxsplit=1)))
        text = None
        anchor = None

        if len(parts) == 2:
            target, text = parts
        else:
            target = parts[0]

        is_category = target[0] == '@'

        if is_category:
            title = target[1:]
        else:
            title, anchor = self._split_title(target)

        if not self._check_title(title):
            return _nodes.TextNode(text=f'{self.open_delimiter}{wikicode}{self.close_delimiter}')
        if is_category:
            return _nodes.CategoryNode(title=title, sort_key=text)
        return _nodes.InternalLinkNode(page_title=title, anchor=anchor, text=text)

    @staticmethod
    def _split_title(title: str) -> typ.Tuple[str, typ.Optional[str]]:
        parts = title.split('#', maxsplit=1)
        anchor = None
        if len(parts) == 2:
            title, anchor = map(str.strip, parts)
        else:
            title = parts[0].strip()
        return title, anchor

    @staticmethod
    def _check_title(page_title: str):
        from .. import settings
        return not re.search(settings.INVALID_TITLE_REGEX, page_title)


class ExternalLinkTag(NonHTMLTag):
    def __init__(self):
        super().__init__('external_link', '[(', ')]', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        from ..api import titles as api_titles

        parts = wikicode.split('|', maxsplit=1)
        text = None

        if len(parts) == 2:
            url, text = map(str.strip, parts)
        else:
            url = parts[0].strip()

        try:
            parse_result = url_parse.urlparse(url)
        except ValueError:
            return _nodes.TextNode(text=f'{self.open_delimiter}{wikicode}{self.close_delimiter}')

        # Convert to internal link if URL’s hostname is in settings.ALLOWED_HOSTS.
        if parse_result.hostname in dj_conf.settings.ALLOWED_HOSTS:
            prefix = api_titles.get_wiki_url_path()
            path = parse_result.path
            title = api_titles.title_from_url(path[path.index(prefix) + len(prefix):])
            anchor = parse_result.fragment
            params = url_parse.parse_qs(parse_result.query)
            # noinspection PyTypeChecker
            return _nodes.InternalLinkNode(title, anchor, params, text)

        return _nodes.ExternalLinkNode(url=url, text=text)


class ImageOrVideoTag(NonHTMLTag):
    def __init__(self):
        super().__init__('image_video', '[{', '}]', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        parts = wikicode.split('|', maxsplit=1)
        width = None
        legend = None

        if len(parts) == 2:
            file_name, params = map(str.strip, parts)
            legend, width = self._split_params(params)
        else:
            file_name = parts[0].strip()
        if not self._check_file_name(file_name):
            return _nodes.TextNode(text=f'{self.open_delimiter}{wikicode}{self.close_delimiter}')

        return _nodes.ImageOrVideoNode(file_name=file_name, width=width, legend=legend)

    @staticmethod
    def _split_params(params: str) -> typ.Tuple[str, typ.Optional[str]]:
        parts = params.split('|', maxsplit=1)
        width = None
        if len(parts) == 2:
            width, legend = map(str.strip, parts)
        else:
            legend = parts[0].strip()
        return legend, width

    @staticmethod
    def _check_file_name(file_name: str):
        from .. import settings
        return (not re.search(settings.INVALID_TITLE_REGEX, file_name)
                and file_name[file_name.rindex('.') + 1:] in settings.MEDIA_FORMATS)


class BoldTextTag(NonHTMLTag):
    def __init__(self):
        super().__init__('bold', '**', '**', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.BoldTextNode(wikicode)


class ItalicTextTag(NonHTMLTag):
    def __init__(self):
        super().__init__('italic', '//', '//', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.ItalicTextNode(wikicode)


class UnderlinedTextTag(NonHTMLTag):
    def __init__(self):
        super().__init__('underlined', '__', '__', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.UnderlinedTextNode(wikicode)


class StrikethroughTextTag(NonHTMLTag):
    def __init__(self):
        super().__init__('strikethrough', '~~', '~~', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.StrikethroughTextNode(wikicode)


class OverlinedTextTag(NonHTMLTag):
    def __init__(self):
        super().__init__('overlined', '++', '++', multiline=False, auto_recursive=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.OverlinedTextNode(wikicode)
