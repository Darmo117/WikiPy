from __future__ import annotations

from ._magic_keywords import *
from ._nodes import *
from ._tags import *

__all__ = [
    'WikicodeParser',
    'WikicodeNode',
    'RedirectNode',
    'HtmlTag',
    'MagicKeyword',
]


def register_default():
    default_html_tags = [
        # TODO
    ]
    for tag in default_html_tags:
        WikicodeParser.register_tag(tag)
    default_magic_keywords = [
        CurrentYearKeyword(local=False),
        CurrentMonthKeyword(local=False, padded=False),
        CurrentMonthKeyword(local=False, padded=True),
        CurrentMonthNameKeyword(local=False, abbr=False),
        CurrentMonthNameKeyword(local=False, abbr=True),
        CurrentDayKeyword(local=False, padded=False),
        CurrentDayKeyword(local=False, padded=True),
        CurrentDayOfWeekKeyword(local=False),
        CurrentDayNameKeyword(local=False),
        CurrentTimeKeyword(local=False),
        CurrentHourKeyword(local=False),
        CurrentMinuteKeyword(local=False),
        CurrentWeekKeyword(local=False),

        CurrentYearKeyword(local=True),
        CurrentMonthKeyword(local=True, padded=False),
        CurrentMonthKeyword(local=True, padded=True),
        CurrentMonthNameKeyword(local=True, abbr=False),
        CurrentMonthNameKeyword(local=True, abbr=True),
        CurrentDayKeyword(local=True, padded=False),
        CurrentDayKeyword(local=True, padded=True),
        CurrentDayOfWeekKeyword(local=True),
        CurrentDayNameKeyword(local=True),
        CurrentTimeKeyword(local=True),
        CurrentHourKeyword(local=True),
        CurrentMinuteKeyword(local=True),
        CurrentWeekKeyword(local=True),

        CurrentTimestampKeyword(),

        SiteNameKeyword(),
        ServerNameKeyword(),
        CurrentVersionKeyword(),
        SiteLanguageKeyword(),

        WritingDirectionMarkKeyword(),
        PageIdKeyword(),
        PageLanguageKeyword(),

        RevisionIdKeyword(),
        RevisionYearKeyword(),
        RevisionMonthKeyword(padded=False),
        RevisionMonthKeyword(padded=True),
        RevisionDayKeyword(padded=False),
        RevisionDayKeyword(padded=True),
        RevisionTimestampKeyword(),
        RevisionUserKeyword(),
        RevisionSizeKeyword(),

        NamespaceNameKeyword(),
        NamespaceIdKeyword(),
        PageTitleKeyword(),
        FullPageTitleKeyword(),
        UsernameKeyword(),
    ]
    for mk in default_magic_keywords:
        WikicodeParser.register_magic_keyword(mk)


def _init_special_tags() -> typ.Dict[str, NonHtmlTag]:
    tags = [
        InternalLinkTag(),
        ExternalLinkTag(),
        BoldTextTag(),
        ItalicTextTag(),
        UnderlinedTextTag(),
        StrikethroughTextTag(),
        OverlinedTextTag(),
        ImageOrVideoTag(),
    ]
    return {t.open_delimiter: t for t in tags}


class WikicodeParser:
    # TODO appliquer la regex des titres
    REDIRECT_PATTERN = re.compile(r'@REDIRECT\[\[([^\n]+?)(?:#([^\n]+?))?]]')
    MAX_DEPTH = 50  # TODO changer après tests

    # States
    TEXT = 'text'
    SPECIAL_TAG = 'special_tag'
    HTML_TAG = 'html_tag'
    DELIMITER = 'delimiter'

    __magic_keywords: typ.Dict[str, MagicKeyword] = {}
    __special_tags: typ.Dict[str, NonHtmlTag] = _init_special_tags()
    __html_tags: typ.Dict[str, HtmlTag] = {}

    @classmethod
    def register_tag(cls, tag: HtmlTag):
        if tag.name in cls.__html_tags:
            raise ValueError(f'attempt to register two tags with the same name "{tag.name}"')
        cls.__html_tags[tag.name] = tag

    @classmethod
    def registered_tags(cls) -> typ.Dict[str, HtmlTag]:
        return cls.__html_tags

    @classmethod
    def register_magic_keyword(cls, mk: MagicKeyword):
        if mk.name in cls.__magic_keywords:
            raise ValueError(f'attempt to register two magic keywords with the same name "{mk.name}"')
        cls.__magic_keywords[mk.name] = mk

    @classmethod
    def registered_magic_keywords(cls) -> typ.Dict[str, MagicKeyword]:
        return cls.__magic_keywords

    @staticmethod
    def make_safe(text: str) -> str:
        return text.replace('<', '&lt;').replace('>', '&gt;')

    def __init__(self):
        self.__max_depth_reached = False
        self.__delimiters_starts = {t.open_delimiter[0] for t in self.__special_tags.values()}

    @property
    def max_depth_reached(self) -> bool:
        return self.__max_depth_reached

    def parse_wikicode(self, wikicode: str, context, no_redirect: bool = False) \
            -> typ.Union[DocumentNode, RedirectNode]:
        """
        Parses the given wikicode.

        :param wikicode: The wikicode to parse.
        :param context: The context to use.
        :type context: WikiPy_app.page_context.PageContext
        :param no_redirect: If true and the wikicode is a redirection, this redirection will not be followed and a
                            RedirectNode will be returned instead.
        :return: The parsed wikicode as a DocumentNode or RedirectNode.
        """
        return self._parse_wikicode_impl(wikicode, context, 0, no_redirect, {})

    def _parse_wikicode_impl(self, wikicode: str, context, depth: int, no_redirect: bool,
                             variables_values: typ.Dict[str, str]) -> typ.Union[DocumentNode, RedirectNode]:
        """
        Parses the given wikicode.

        :param wikicode: The wikicode to parse.
        :param context: The context to use.
        :type context: WikiPy_app.page_context.PageContext
        :param depth: The recursive parsing depth. If it is greater than the defined limit, the parsing stops for the
                      concerned branch and a DocumentNode containing the raw text is returned.
        :param no_redirect: If true and the wikicode is a redirection, this redirection will not be followed and a
                            RedirectNode will be returned instead.
        :param variables_values: A dictionary defining the values of variables.
        :return: The parsed wikicode as a DocumentNode or RedirectNode.
        """
        from .. import api

        wikicode = wikicode.strip()

        # Maximum depth reached, stop parsing
        if depth > self.MAX_DEPTH:
            self.__max_depth_reached = True
            return DocumentNode(ParagraphNode(TextNode(text=self.make_safe(wikicode))))

        if redirect := self.get_redirect(wikicode):
            page_title, anchor = redirect
            if no_redirect:
                root_node = RedirectNode(target_page=page_title, anchor=anchor)
            else:  # TODO attention aux boucles de redirection
                ns, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
                revision = api.get_page_revision(ns, title)
                if revision:
                    root_node = self._parse_wikicode_impl(revision.content, context, depth + 1, no_redirect=False,
                                                          variables_values=variables_values)
                else:
                    root_node = DocumentNode(ParagraphNode(TextNode(text=self.make_safe(wikicode))))
        else:
            wikicode = self._substitute_magic_keywords(wikicode, context)
            # wikicode = self._substitute_variables(wikicode, variables_values)
            # wikicode = self._substitute_transclusions(wikicode)
            # wikicode = self._substitute_functions(wikicode)
            wikicode = wikicode.replace('{{!}}', '|')
            root_node = DocumentNode(*self._parse_document(wikicode))

        return root_node

    def _substitute_magic_keywords(self, wikicode: str, context) -> str:
        """
        Substitutes magic keywords with their value.

        :param wikicode: The wikicode to perform substitutions on.
        :param context: The context to use.
        :type context: WikiPy_app.page_context.PageContext
        :return: The substituted wikicode.
        """
        for name, mk in self.__magic_keywords.items():
            token = f'{{{{{name}}}}}'
            if token in wikicode:
                wikicode = wikicode.replace(token, mk.get_value(context))
        return wikicode

    def _substitute_variables(self, wikicode: str, variables_values: typ.Dict[str, str]) -> str:
        open_delimiter = '{['
        close_delimiter = ']}'
        result = ''
        buffer = ''
        in_variable = False
        in_name = False
        var_name = ''
        var_default = ''
        # Number of times the variable opening delimiter has been encountered
        opened_tags = 0
        i = 0

        while i < len(wikicode):
            c = wikicode[i]
            next_c = wikicode[i + 1] if i < len(wikicode) - 1 else ''

            if not in_variable:
                if c + next_c == open_delimiter:
                    result += buffer
                    in_variable = True
                    in_name = True
                    buffer = ''
                else:
                    buffer += c
            elif in_name:
                if re.match(r'[ \w]', c):
                    var_name += c
                elif c == '|' or c + next_c == close_delimiter:
                    in_name = False
                else:
                    buffer += open_delimiter + var_name
                    in_variable = False
                    in_name = False
            else:
                if c + next_c == open_delimiter:
                    opened_tags += 1
                    buffer += c + next_c
                    i += 1
                elif c + next_c == close_delimiter:
                    opened_tags -= 1
                    if opened_tags == 0:
                        buffer = ''
                        in_variable = False
                        i += 1
                else:
                    buffer += c

            i += 1

        return result

    def _substitute_functions(self, wikicode: str) -> str:
        return wikicode  # TEMP

    # TODO attention aux boucles de redirection
    def _substitute_transclusions(self, wikicode: str) -> str:
        return wikicode  # TEMP

    def _parse_document(self, wikicode: str) -> typ.Sequence[WikicodeNode]:
        def new_paragraph(b: str):
            nonlocal paragraph

            if b.strip():
                paragraph.append(TextNode(text=self.make_safe(b)))
            if not paragraph.is_empty:
                nodes.append(paragraph)
                paragraph = ParagraphNode()

        state = self.TEXT
        tag = None
        nodes = []
        paragraph = ParagraphNode()
        buffer = ''
        # Number of times the current delimiter has been encountered for the current tag
        opened_tags = 0
        i = 0

        while i < len(wikicode):
            c = wikicode[i]
            next_c = wikicode[i + 1] if i < len(wikicode) - 1 else ''
            # print(repr(c), state)  # DEBUG

            if state == self.TEXT:
                if t := self.__special_tags.get(c + next_c):
                    tag = t
                    opened_tags = 1
                    if buffer:
                        paragraph.append(TextNode(text=self.make_safe(buffer)))
                        buffer = ''
                    state = self.SPECIAL_TAG
                    i += 1
                elif c + next_c == '\n\n':
                    new_paragraph(buffer)
                    buffer = ''
                    i += 1
                elif c == '<':  # Escape HTML tags
                    buffer += '&lt;'
                else:
                    buffer += c

            elif state == self.SPECIAL_TAG:
                if c == '\n' and not tag.multiline:
                    buffer = tag.open_delimiter + buffer
                    state = self.TEXT
                    i -= 1
                elif tag.auto_recursive and tag.open_delimiter != tag.close_delimiter \
                        and c + next_c == tag.open_delimiter:
                    opened_tags += 1
                    buffer += c + next_c
                    i += 1
                elif c + next_c == tag.close_delimiter:
                    opened_tags -= 1
                    if opened_tags == 0:
                        node = tag.parse_wikicode(buffer)
                        if node.is_inline:
                            paragraph.append(node)
                        else:
                            new_paragraph('')
                            nodes.append(node)
                        buffer = ''
                        state = self.TEXT
                        i += 1
                        tag = None
                else:
                    buffer += c

            i += 1
        if tag:
            buffer = tag.open_delimiter + buffer
        new_paragraph(buffer)
        print('Parser nodes:', nodes)  # DEBUG

        return nodes

    @classmethod
    def get_redirect(cls, wikicode: str) -> typ.Optional[typ.Tuple[str, typ.Optional[str]]]:
        from .. import api

        if m := cls.REDIRECT_PATTERN.fullmatch(wikicode.strip()):
            title = m.group(1)
            anchor = m.group(2) if m.lastindex == 2 else None
            try:
                api.check_title(title)
            except (api.BadTitleException, api.EmptyPageTitleException):
                pass
            else:
                return title, anchor
        return None

    @staticmethod
    def paste_sections(header: str, sections: typ.Dict[int, str]):
        return header + '\n' + '\n'.join(sections.values())

    # TODO
    # noinspection PyUnusedLocal
    @staticmethod
    def split_sections(wikicode: str, level: int = 1) -> typ.Tuple[str, typ.Dict[int, str]]:
        header = ''
        sections = {}
        section_found = False
        section_index = 1

        for line in wikicode.split('\n'):
            if m := re.fullmatch(r'(=+)\s*.+?\s*\1', line):
                section_level = len(m.group(1))
                # if section_level <
                sections[section_index] = line + '\n'
                section_index += 1
                section_found = True
            elif not section_found:
                header += line + '\n'
            else:
                sections[section_index] += line + '\n'

        # Remove trailing \n
        header = header[:-1]
        for t in sections:
            sections[t] = sections[t][:-1]

        return header, sections


#####################
# Substitution tags #
#####################


class SubstitutionTag(abc.ABC):
    def __init__(self, open_delimiter: str, close_delimiter: str):
        self.__open_delimiter = open_delimiter
        self.__close_delimiter = close_delimiter

    @property
    def open_delimiter(self) -> str:
        return self.__open_delimiter

    @property
    def close_delimiter(self) -> str:
        return self.__close_delimiter

    @abc.abstractmethod
    def substitute(self, wikicode: str, params) -> str:
        pass


class TransclusionTag(SubstitutionTag):
    def __init__(self):
        super().__init__('{{', '}}')

    def substitute(self, wikicode, params):
        pass  # TODO


class ParameterTag(SubstitutionTag):
    def __init__(self):
        super().__init__('{[', ']}')

    def substitute(self, wikicode, params):
        pass  # TODO


class FunctionTag(SubstitutionTag):
    def __init__(self):
        super().__init__('{(', ')}')

    def substitute(self, wikicode, params):
        pass  # TODO
