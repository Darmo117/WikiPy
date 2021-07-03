"""This module defines the base parser nodes as well as the default ones.

Nodes are used to render the document they represent.
"""
from __future__ import annotations

import abc
import typing as typ


class WikicodeNode(abc.ABC):
    def __init__(self, inline: bool):
        """The base class for nodes.
        Nodes are used to render the document they represent.

        :param inline: Indicates whether this node represents inline text.
        """
        self.__inline = inline
        self._internal_nodes = []

    @property
    def is_inline(self):
        """Whether this node represents inline text."""
        return self.__inline

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        """If this node still has content to parse, it should be accessible through this property.

        :return: The text to parse or None if there is none.
        """
        return None

    def set_parsed_content_nodes(self, nodes: typ.Sequence[WikicodeNode]):
        """For nodes with text to parse, sets the nodes corresponding to the parsed text.

        :param nodes: The nodes resulting from the content_to_parse text.
        """
        self._internal_nodes = nodes

    def substitute_placeholders(self, placeholders: typ.Dict[str, str]):
        """Substitutes remaining placeholders in the text of
        this node and all its sub-nodes if any.

        :param placeholders: The placeholders registry.
        """
        for node in self._internal_nodes:
            node.substitute_placeholders(placeholders)

    @abc.abstractmethod
    def render(self, skin, context) -> str:
        """Renders this node as HTML.
        Returned string is considered HTML-safe.

        :param skin: The current skin.
        :type skin: WikiPy.skins.Skin
        :param context: The context for the page being rendered.
        :type context: WikiPy.page_context.PageContext
        :return: The HTML code.
        """
        pass

    def get_categories(self) -> typ.List[CategoryNode]:
        """Returns the list of CategoryNode instances among this node’s subnodes.
        If this node is itself a CategoryNode, it returns itself.
        """
        return [category for node in self._internal_nodes for category in node.get_categories()]

    def _render_internal_nodes(self, skin, context):
        """
        Renders this node’s internal nodes as HTML.
        This method is meant to be used by subclasses in their render() method.

        :param skin: The current skin.
        :type skin: WikiPy.skins.Skin
        :param context: The context for the page being rendered.
        :type context: WikiPy.page_context.PageContext
        :return: The HTML code.
        """
        return ''.join(map(lambda n: n.render(skin, context), self._internal_nodes))

    @staticmethod
    def _do_substitute_placeholders(text: str, placeholders: typ.Dict[str, str]) -> str:
        """Helper method to substitute placeholder in a given string.

        :param text: The text to substitute from.
        :param placeholders: The placeholders registry.
        :return: The modified text.
        """
        for ph, subst in placeholders.items():
            text = text.replace(ph, subst)
        return text


class TopLevelNode(WikicodeNode, abc.ABC):
    """A top level node is a node that is at the root of the page document."""

    def __init__(self):
        super().__init__(inline=False)


class InlineNode(WikicodeNode, abc.ABC):
    """An inline node is a node that is part of a paragraph, title or table cell."""

    def __init__(self):
        super().__init__(inline=True)


class DocumentNode(TopLevelNode):
    def __init__(self, *nodes: TopLevelNode):
        """The Document node is the topmost node in any node tree representing a page.

        :param nodes: The list of all its subnodes.
        """
        super().__init__()
        self._internal_nodes = nodes

    @property
    def is_empty(self) -> bool:
        """Whether this document has any subnodes.

        :return: True if this document hasn’t any subnodes, false otherwise.
        """
        return len(self._internal_nodes) == 0

    @property
    def nodes(self) -> typ.Tuple[TopLevelNode]:
        """The list of all direct subnodes of this document."""
        return self._internal_nodes

    def render(self, skin, context):
        return ''.join(map(lambda n: n.render(skin, context), self._internal_nodes))

    def __repr__(self):
        return 'DocumentNode[' + ', '.join([repr(node) for node in self.nodes]) + ']'


class TitleNode(TopLevelNode):
    def __init__(self, content: WikicodeNode, level: int):
        """The Title node represents a section title.

        :param content: The title’s text.
        :param level: The title’s section level.
        """
        super().__init__()
        self.__content = content
        self.__level = level

    @property
    def content(self) -> WikicodeNode:
        """The title text."""
        return self.__content

    @property
    def level(self) -> int:
        """The section level."""
        return self.__level

    def render(self, skin, context) -> str:
        pass  # TODO

    def __repr__(self):
        return f'TitleNode[content={self.content!r},level={self.level}]'


class ParagraphNode(TopLevelNode):
    def __init__(self, *text_nodes: WikicodeNode):
        """Paragraph nodes are top-level nodes that contain a list of text nodes.

        :param text_nodes: The list on text nodes this paragraph contains.
        """
        super().__init__()
        self._internal_nodes = list(text_nodes)

    @property
    def is_empty(self):
        """Whether this paragraph has any subnodes.

        :return: True if this paragraph hasn’t any subnodes, false otherwise.
        """
        return len(self._internal_nodes) == 0

    @property
    def nodes(self) -> typ.Tuple[WikicodeNode]:
        """The list of all direct subnodes of this paragraph."""
        return tuple(self._internal_nodes)

    def append(self, text_node: WikicodeNode):
        """Appends a new text node at the end of this paragraph.

        :param text_node: The node to append.
        """
        self._internal_nodes.append(text_node)

    def render(self, skin, context):
        return '<p>' + ''.join(map(lambda n: n.render(skin, context), self.nodes)) + '</p>'

    def __repr__(self):
        return 'ParagraphNode[' + ', '.join([repr(node) for node in self.nodes]) + ']'


class CategoryNode(InlineNode):
    def __init__(self, title: str, sort_key: str = None):
        """Category nodes represent the categories the document they appear in belongs to.

        :param title: The category title.
        :param sort_key: The document’s sort key in this category.
        """
        from ..api import titles as api_titles

        super().__init__()
        self.__title = api_titles.get_actual_page_title(title)
        self.__sort_key = sort_key

    @property
    def title(self) -> str:
        """This category’s title."""
        return self.__title

    @property
    def sort_key(self) -> str:
        """The sort key of the document for this category."""
        return self.__sort_key

    def render(self, skin, context) -> str:
        return ''

    def get_categories(self) -> typ.List[CategoryNode]:
        return [self]

    def __repr__(self):
        return f'CategoryNode[title={self.__title!r},sort_key={self.__sort_key!r}]'


class TextNode(InlineNode):
    def __init__(self, text: str):
        """Text nodes represent links, styled or plain text.

        :param text: The text of this node.
        """
        super().__init__()
        self.__text = text

    @property
    def text(self) -> str:
        """This node’s text."""
        return self.__text

    def substitute_placeholders(self, placeholders: typ.Dict[str, str]):
        if self._internal_nodes:
            super().substitute_placeholders(placeholders)
        else:
            self.__text = self._do_substitute_placeholders(self.__text, placeholders)

    def render(self, skin, context):
        return self.text

    def __repr__(self):
        return f'TextNode[text={self.text!r}]'


class InternalLinkNode(TextNode):
    def __init__(self, page_title: str, anchor: str = None, params: typ.Dict[str, typ.Union[str, typ.List[str]]] = None,
                 text: str = None):
        """This node represents a link to another page on the same wiki.

        :param page_title: The page’s title.
        :param anchor: The optional anchor in this page.
        :param params: Additional URL parameters.
        :param text: The optional text to display in place of the URL.
        """
        from ..api import titles as api_titles

        page_title = api_titles.get_actual_page_title(page_title)

        if not text:
            if text is None:
                text = page_title
            else:  # Remove namespace from text if no text specified after |
                text = api_titles.extract_title(page_title)
            if anchor:
                text += '#' + anchor
        super().__init__(text=text)
        self.__page_title = page_title
        self.__anchor = anchor
        self.__params = params or {}

    @property
    def page_title(self) -> str:
        """Title of the page this link points to."""
        return self.__page_title

    @property
    def anchor(self) -> typ.Optional[str]:
        """Anchor this link may point to in the target page."""
        return self.__anchor

    @property
    def params(self) -> typ.Dict[str, typ.Union[str, typ.List[str]]]:
        """Additional URL parameters."""
        return self.__params

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return skin.format_internal_link(
            context.language,
            current_page_title=context.page.full_title,
            page_title=self.page_title,
            text=self._render_internal_nodes(skin, context),
            anchor=self.anchor,
            url_params=self.params
        )

    def __repr__(self):
        return f'InternalLinkNode[page_title={self.page_title!r},anchor={self.anchor!r},params={self.params!r},' \
               f'text={self.text!r}]'


class ExternalLinkNode(TextNode):
    def __init__(self, url: str, text: str = None):
        """This node represents a link to an URL outside of the wiki (may be the same site).

        :param text: The optional text to display in place of the URL.
        """
        super().__init__(text=text or url)
        self.__url = url

    @property
    def url(self) -> str:
        """The URL this link points to."""
        return self.__url

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return skin.format_external_link(self.url, self._render_internal_nodes(skin, context))

    def __repr__(self):
        return f'ExternalLinkNode[url={self.url!r},text={self.text!r}]'


class BoldTextNode(TextNode):
    """This node represents bold text."""

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return f'<strong class="text-bold">{self._render_internal_nodes(skin, context)}</strong>'

    def __repr__(self):
        return f'BoldTextNode[text={repr(self.text)}]'


class ItalicTextNode(TextNode):
    """This node represents italicized text."""

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return f'<em class="text-italic">{self._render_internal_nodes(skin, context)}</em>'

    def __repr__(self):
        return f'ItalicTextNode[text={self.text!r}]'


class UnderlinedTextNode(TextNode):
    """This node represents underlined text."""

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return f'<span class="text-underlined">{self._render_internal_nodes(skin, context)}</span>'

    def __repr__(self):
        return f'UnderlinedTextNode[text={self.text!r}]'


class OverlinedTextNode(TextNode):
    """This node represents text with a line above it."""

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return f'<span class="text-overlined">{self._render_internal_nodes(skin, context)}</span>'

    def __repr__(self):
        return f'OverlinedTextNode[text={self.text!r}]'


class StrikethroughTextNode(TextNode):
    """This node represents strikethrough text."""

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.text

    def render(self, skin, context):
        return f'<s class="text-stroke">{self._render_internal_nodes(skin, context)}</s>'

    def __repr__(self):
        return f'Strikethrough[text={self.text!r}]'


class FileNode(WikicodeNode):
    def __init__(self, file_name: str, width: str = None, legend: str = None):
        """This node represents an embedded multimedia file.

        :param file_name: The file’s name.
        :param width: The display width. May be a CSS size value or 'thumb' to display it as a thumbnail.
            Mainly intended for image and video files.
        :param legend: The optional legend to display alongside the embedded file.
        """
        super().__init__(inline=width != 'thumb')
        self.__file_name = file_name
        self.__width = width
        self.__legend = legend

    @property
    def file_name(self) -> str:
        """The file’s name."""
        return self.__file_name

    @property
    def width(self) -> str:
        """The file’s display width. May be a CSS size value or 'thumb' for thumbnails."""
        return self.__width

    @property
    def legend(self) -> str:
        """The optional legend to display alongside the embedded file."""
        return self.__legend

    @property
    def content_to_parse(self) -> typ.Optional[str]:
        return self.__legend

    def render(self, skin, context):
        from ..api import pages as api_pages
        from .. import media_backends

        metadata = api_pages.get_file_metadata(self.file_name)

        if not metadata:
            return ''  # TODO

        tooltip = context.language.translate('media.button.size_up.tooltip')
        thumb = self.width == 'thumb'
        width = self.width if not thumb else f'{context.user.data.max_image_thumbnail_size}px'
        classes = []
        if thumb:
            classes.append('pull-right')

        url = metadata.url
        mime_type_full = metadata.mime_type_full
        media_type = metadata.media_type
        template = f"""
<figure class="img-thumbnail {' '.join(classes)}">
  {{tag}}
  <figcaption style="max-width: {width or ''}">
    <a href="#" role="button" class="mdi mdi-resize pull-right" title="{tooltip}"></a>
    {self._render_internal_nodes(skin, context) or ''}
  </figcaption>
</figure>
""".strip()

        if media_type == media_backends.FileMetadata.VIDEO:
            no_video = context.language.translate('media.format.video.not_supported')
            return template.format(tag=f"""
<video controls poster="{metadata.video_thumbnail or ''}" style="width: {width or ''};">
  <source src="{url}" type="{mime_type_full}">
  <p>{no_video}</p>
</video>
""".strip())

        elif media_type == media_backends.FileMetadata.AUDIO:
            no_audio = context.language.translate('media.format.audio.not_supported')
            return template.format(tag=f"""
<audio controls>
  <source src="{url}" type="{mime_type_full}">
  <p>{no_audio}</p>
</audio>
""".strip())

        elif media_type == media_backends.FileMetadata.IMAGE:
            return template.format(
                tag=f'<img src="{url}" alt="{self.file_name}" style="width: {width or ""};" />'
            )

        message = context.language.translate('media.format.not_supported', media_type=media_type)
        return f'<span class="wpy-parser-error">{message}</span>'

    def __repr__(self):
        return f'ImageOrVideoNode[file_name={self.file_name!r},width={self.width!r},legend={self.legend!r}]'


class ExtendedHTMLTagNode(WikicodeNode, abc.ABC):
    def __init__(self, name: str, inline: bool, content: str, **attributes: str):
        """Extended HTML tags are special tags that use the HTML syntax.

        :param name: The tag’s name.
        :param inline: Whether this tag is inline or not.
        :param content: The tag’s content.
        :param attributes: The tag’s attributes.
        """
        super().__init__(inline=inline)
        self.__name = name
        self.__attributes = attributes
        self.__content = content

    @property
    def name(self) -> str:
        """This tag’s name."""
        return self.__name

    @property
    def attributes(self) -> typ.Dict[str, str]:
        """This tag’s attributes."""
        return self.__attributes.copy()

    @property
    def content(self):
        return self.__content

    def __repr__(self):
        return f'ExtendedHtmlNode[name={self.__name},attributes={self.__attributes},content={self.__content}]'


class RedirectNode(TopLevelNode):
    def __init__(self, target_page: str, anchor: str = None):
        """This special node represents a redirection.
        Redirect nodes should never be inside a Document node.

        :param target_page: The title of the page to redirect to.
        :param anchor: The optional anchor in the target page.
        """
        super().__init__()
        self.__target_page = target_page
        self.__anchor = anchor

    @property
    def target_page(self) -> str:
        """The title of the page to redirect to."""
        return self.__target_page

    @property
    def anchor(self) -> typ.Optional[str]:
        """The optional anchor in the target page."""
        return self.__anchor

    def render(self, skin, context):
        text = self.target_page
        if self.anchor:
            text += '#' + self.anchor
        link = skin.format_internal_link(
            context.language,
            context.page.full_title,
            self.target_page,
            anchor=self.anchor,
            text=text
        )

        return f'<span id="wpy-redirect-link"><span class="mdi mdi-subdirectory-arrow-right"></span> {link}</span>'

    def __repr__(self):
        return f'RedirectNode[target_page={self.target_page!r},anchor={self.anchor!r}]'
