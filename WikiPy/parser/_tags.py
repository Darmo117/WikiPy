"""This module defines the base parser tags as well as the default ones.

Tags are used to parse wikicode and generate nodes that will later be used to render the HTML document.
"""
import abc
import re
import typing as typ
import urllib.parse as url_parse

import django.conf as dj_conf

from . import _nodes


class Tag(abc.ABC):
    def __init__(self, name: str, auto_recursive: bool):
        """The base class for tags.
        Tags are used to parse wikicode and generate nodes that will later be used to render the HTML document.

        :param name: The tag’s name.
        :param auto_recursive: Whether this tag can include other instances of itself.
        """
        self.__name = name
        self.__auto_recursive = auto_recursive

    @property
    def name(self) -> str:
        """This tag’s name."""
        return self.__name

    @property
    def auto_recursive(self) -> bool:
        """Whether this tag can include other instances of itself."""
        return self.__auto_recursive

    @abc.abstractmethod
    def parse_wikicode(self, wikicode: str) -> _nodes.WikicodeNode:
        """
        Parses the given wikicode and returns the corresponding node.

        :param wikicode: The wikicode to parse.
        :return: A node.
        """
        pass


#############
# HTML tags #
#############


class ExtendedHTMLTag(Tag, abc.ABC):
    def __init__(self, name: str, inline: bool, auto_recursive: bool, *attributes: str):
        """Base class for HTML-like tags.
        This type of tag uses the same syntax as regular HTML tags.

        :param name: The tag’s name.
        :param inline: Whether this tag is inline or not.
        :param auto_recursive: Whether this tag can include other instances of itself.
        :param attributes: The attributes this tag accepts. Any encountered attribute
            that is not in this list will be ignored and will be absent from the resulting HTML page.
        """
        super().__init__(name, auto_recursive)
        self.__name = name
        self.__inline = inline
        self.__attributes = attributes

    @property
    def inline(self) -> bool:
        """Whether this tag is inline or not."""
        return self.__inline

    @property
    def attributes(self) -> typ.Tuple[str]:
        """The attributes this tag accepts."""
        return self.__attributes


#################
# Non-HTML tags #
#################


class NonHTMLTag(Tag, abc.ABC):
    def __init__(self, name: str, open_delimiter: str, close_delimiter: str, multiline: bool):
        """Non-HTML tags have opening and closing delimiters.
        This type of tag cannot be defined through extensions.

        :param name: Tag’s internal name.
        :param open_delimiter: Opening delimiter, must be exactly 2 characters long.
        :param close_delimiter: Closing delimiter, must be exactly 2 characters long.
        :param multiline: Whether the content of this tag can span multiple lines.
        """
        super().__init__(name, auto_recursive=False)
        if len(open_delimiter) != 2 or len(close_delimiter) != 2:
            raise ValueError('opening and closing tag delimiters should be exactly 2 characters long')
        self.__open_delimiter = open_delimiter
        self.__close_delimiter = close_delimiter
        self.__multiline = multiline

    @property
    def open_delimiter(self) -> str:
        """This tags opening delimiter."""
        return self.__open_delimiter

    @property
    def close_delimiter(self) -> str:
        """This tags closing delimiter."""
        return self.__close_delimiter

    @property
    def multiline(self) -> bool:
        """Whether the content of this tag can span multiple lines."""
        return self.__multiline


class InternalLinkOrCategoryTag(NonHTMLTag):
    """This tag is used to create links to other pages on the same wiki or to indicate categories.
    Links presenting an @ sign right after the opening delimiter will be considered as a category.
    """

    def __init__(self):
        super().__init__('internal_link', '[[', ']]', multiline=False)

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
    """This tag is used to create links to URLs outside of the wiki (may be the same site).
    If an external link points to another page in the same wiki, it will be converted to an internal link.
    """

    def __init__(self):
        super().__init__('external_link', '[(', ')]', multiline=False)

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

        # Convert to internal link if URL’s hostname is in settings.ALLOWED_HOSTS and the path matches the wiki path.
        if parse_result.hostname in dj_conf.settings.ALLOWED_HOSTS:
            prefix = api_titles.get_wiki_url_path()
            path = parse_result.path

            if path.startswith(prefix):
                title = api_titles.title_from_url(path[path.index(prefix) + len(prefix):])
                anchor = parse_result.fragment
                params: typ.Dict[typ.AnyStr, typ.List[typ.AnyStr]] = url_parse.parse_qs(parse_result.query)
                return _nodes.InternalLinkNode(title, anchor, params, text)

        return _nodes.ExternalLinkNode(url=url, text=text)


class FileTag(NonHTMLTag):
    """This tag is used to embed multimedia files."""

    def __init__(self):
        super().__init__('file', '[{', '}]', multiline=False)

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

        return _nodes.FileNode(file_name=file_name, width=width, legend=legend)

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
    """This tag is used to make text bold."""

    def __init__(self):
        super().__init__('bold', '**', '**', multiline=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.BoldTextNode(wikicode)


class ItalicTextTag(NonHTMLTag):
    """This tag is used to italicize text."""

    def __init__(self):
        super().__init__('italic', '//', '//', multiline=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.ItalicTextNode(wikicode)


class UnderlinedTextTag(NonHTMLTag):
    """This tag is used to underline text."""

    def __init__(self):
        super().__init__('underlined', '__', '__', multiline=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.UnderlinedTextNode(wikicode)


class StrikethroughTextTag(NonHTMLTag):
    """This tag is used to strike text."""

    def __init__(self):
        super().__init__('strikethrough', '~~', '~~', multiline=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.StrikethroughTextNode(wikicode)


class OverlinedTextTag(NonHTMLTag):
    """This tag is used to overline text."""

    def __init__(self):
        super().__init__('overlined', '++', '++', multiline=False)

    def parse_wikicode(self, wikicode: str):
        return _nodes.OverlinedTextNode(wikicode)
