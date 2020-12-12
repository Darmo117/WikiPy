from __future__ import annotations

import abc
import typing as typ


class WikicodeNode(abc.ABC):
    def __init__(self, inline: bool):
        self.__inline = inline

    @property
    def is_inline(self):
        return self.__inline

    @abc.abstractmethod
    def render(self, skin, context) -> str:
        """
        Renders this node as HTML.

        :param skin: The current skin.
        :type skin: WikiPy_app.skins.Skin
        :param context: The context for the page being rendered.
        :type context: WikiPy_app.page_context.PageContext
        :return: The HTML code.
        """
        pass


class TopLevelNode(WikicodeNode, abc.ABC):
    """
    A top level node is a node that is at the root of the page document.
    """

    def __init__(self):
        super().__init__(inline=False)


class InlineNode(WikicodeNode, abc.ABC):
    """
    An inline node is a node that is part of a paragraph, title or table cell.
    """

    def __init__(self):
        super().__init__(inline=True)


class DocumentNode(TopLevelNode):
    def __init__(self, *nodes: TopLevelNode):
        super().__init__()
        self.__nodes = nodes

    @property
    def is_empty(self) -> bool:
        return len(self.__nodes) == 0

    @property
    def nodes(self) -> typ.Tuple[TopLevelNode]:
        return self.__nodes

    def render(self, skin, context):
        return ''.join(map(lambda n: n.render(skin, context), self.__nodes))

    def __repr__(self):
        return 'DocumentNode[' + ', '.join([repr(node) for node in self.nodes]) + ']'


class TitleNode(TopLevelNode):
    def __init__(self, content: WikicodeNode, level: int):
        super().__init__()
        self.__content = content
        self.__level = level

    @property
    def content(self) -> WikicodeNode:
        return self.__content

    @property
    def level(self) -> int:
        return self.__level

    def render(self, skin, context) -> str:
        pass  # TODO

    def __repr__(self):
        return f'TitleNode[content={repr(self.content)},level={self.level}]'


class ParagraphNode(TopLevelNode):
    def __init__(self, *text_nodes: WikicodeNode):
        super().__init__()
        self.__nodes = list(text_nodes)

    @property
    def is_empty(self):
        return len(self.__nodes) == 0

    @property
    def nodes(self) -> typ.Tuple[WikicodeNode]:
        return tuple(self.__nodes)

    def append(self, text_node: WikicodeNode):
        self.__nodes.append(text_node)

    def render(self, skin, context):
        return '<p>' + ''.join(map(lambda n: n.render(skin, context), self.nodes)) + '</p>'

    def __repr__(self):
        return 'ParagraphNode[' + ', '.join([repr(node) for node in self.nodes]) + ']'


class TextNode(InlineNode):
    def __init__(self, text: str):
        super().__init__()
        self.__text = text

    @property
    def text(self) -> str:
        return self.__text

    def render(self, skin, context):
        return self.text

    def __repr__(self):
        return f'TextNode[text={repr(self.text)}]'


class InternalLinkNode(TextNode):
    def __init__(self, page_title: str, anchor: str = None, text: str = None):
        from .. import api

        if not text:
            if text is None:
                text = page_title
            else:  # Remove namespace from text if no text specified after |
                text = api.extract_title(page_title)
            if anchor:
                text += '#' + anchor
        super().__init__(text=text)
        self.__page_title = page_title
        self.__anchor = anchor

    @property
    def page_title(self) -> str:
        return self.__page_title

    @property
    def anchor(self) -> typ.Optional[str]:
        return self.__anchor

    def render(self, skin, context):
        return skin.format_internal_link(context.language, context.page.full_title, page_title=self.page_title,
                                         text=self.text, anchor=self.anchor)

    def __repr__(self):
        return f'InternalLinkNode[page_title={repr(self.page_title)},anchor={repr(self.anchor)},text={repr(self.text)}]'


class ExternalLinkNode(TextNode):
    def __init__(self, url: str, text: str = None):
        super().__init__(text=text or url)
        self.__url = url

    @property
    def url(self) -> str:
        return self.__url

    def render(self, skin, context):
        return skin.format_external_link(self.url, self.text)

    def __repr__(self):
        return f'ExternalLinkNode[url={repr(self.url)},text={repr(self.text)}]'


class BoldTextNode(TextNode):
    def render(self, skin, context):
        return f'<span class="text-bold">{self.text}</span>'

    def __repr__(self):
        return f'BoldTextNode[text={repr(self.text)}]'


class ItalicTextNode(TextNode):
    def render(self, skin, context):
        return f'<span class="text-italic">{self.text}</span>'

    def __repr__(self):
        return f'ItalicTextNode[text={repr(self.text)}]'


class UnderlinedTextNode(TextNode):
    def render(self, skin, context):
        return f'<span class="text-underlined">{self.text}</span>'

    def __repr__(self):
        return f'UnderlinedTextNode[text={repr(self.text)}]'


class OverlinedTextNode(TextNode):
    def render(self, skin, context):
        return f'<span class="text-overlined">{self.text}</span>'

    def __repr__(self):
        return f'OverlinedTextNode[text={repr(self.text)}]'


class StrikethroughTextNode(TextNode):
    def render(self, skin, context):
        return f'<span class="text-stroke">{self.text}</span>'

    def __repr__(self):
        return f'Strikethrough[text={repr(self.text)}]'


class ImageOrVideoNode(WikicodeNode):
    def __init__(self, file_name: str, width: str = None, legend: str = None):
        super().__init__(inline=width != 'thumb')
        self.__file_name = file_name
        self.__width = width
        self.__legend = legend

    @property
    def file_name(self) -> str:
        return self.__file_name

    @property
    def width(self) -> str:
        return self.__width

    @property
    def legend(self) -> str:
        return self.__legend

    def render(self, skin, context):
        from .. import api, media_backends

        metadata = api.get_file_metadata(self.file_name)

        if not metadata:
            return ''  # TODO

        tooltip = context.language.translate('media.button.size_up.tooltip')
        thumb = self.width == 'thumb'
        width = self.width if not thumb else '200px'
        classes = []
        if thumb:
            classes.append('pull-right')

        style = f'style="width: {width};"'

        url = metadata.url
        mime_type_full = metadata.mime_type_full
        media_type = metadata.media_type
        template = f"""
<figure class="img-thumbnail {' '.join(classes)}">
  {{}}
  <figcaption style="max-width: {width or ''}">
    <a href="#" role="button" class="mdi mdi-resize pull-right" title="{tooltip}"></a>
    {self.legend or ''}
  </figcaption>
</figure>
""".strip()

        if media_type == media_backends.FileMetadata.VIDEO:
            no_video = context.language.translate('media.format.video.not_supported')
            return template.format(f"""
<video controls {style}>
  <source src="{url}" type="{mime_type_full}">
  <p>{no_video}</p>
</video>
""".strip())
        elif media_type == media_backends.FileMetadata.AUDIO:
            no_audio = context.language.translate('media.format.audio.not_supported')
            return template.format(f"""
<audio controls {style}>
  <source src="{url}" type="{mime_type_full}">
  <p>{no_audio}</p>
</audio>
""".strip())
        elif media_type == media_backends.FileMetadata.IMAGE:
            return template.format(f'<img src="{url}" alt="{self.file_name}" {style} />')

        message = context.language.translate('media.format.not_supported', media_type=media_type)
        return f'<span class="wpy-parser-error">{message}</span>'

    def __repr__(self):
        return f'ImageOrVideoNode[file_name={repr(self.file_name)},width={repr(self.width)},legend={repr(self.legend)}]'


class HtmlTagNode(WikicodeNode):
    def __init__(self, name: str, inline: bool, **attributes: str):
        super().__init__(inline=inline)
        self.__name = name
        self.__attributes = attributes

    @property
    def name(self) -> str:
        return self.__name

    @property
    def attributes(self) -> typ.Dict[str, str]:
        return self.__attributes.copy()

    def render(self, skin, context):
        pass  # TODO


class RedirectNode(TopLevelNode):
    def __init__(self, target_page: str, anchor: str = None):
        super().__init__()
        self.__target_page = target_page
        self.__anchor = anchor

    @property
    def target_page(self) -> str:
        return self.__target_page

    @property
    def anchor(self) -> typ.Optional[str]:
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
        return f'RedirectNode[target_page={repr(self.target_page)},anchor={repr(self.anchor)}]'
