"""
The parser generates tokens from wikicode.
"""
from __future__ import annotations

import random
import re
import typing as typ

from . import _functions
from . import _magic_keywords
from . import _nodes
from . import _tags
from ._registry import *

WikicodeNode = _nodes.WikicodeNode
RedirectNode = _nodes.RedirectNode
ExtendedHTMLTagNode = _nodes.ExtendedHTMLTagNode
ExtendedHTMLTag = _tags.ExtendedHTMLTag


def load_magic_keywords():
    """Loads all registered magic keywords, including those from extensions."""
    for mk in get_registered_magic_keywords().values():
        # noinspection PyProtectedMember
        WikicodeParser._register_magic_keyword(mk)


def load_functions():
    """Loads all registered parser functions, including those from extensions."""
    for name, function in get_registered_functions().items():
        # noinspection PyProtectedMember
        WikicodeParser._register_function(function, name)


def _init_special_tags() -> typ.Dict[str, _tags.NonHTMLTag]:
    """Returns a mapping containing every special tag (links, bold, etc.) identified by their opening delimiter."""
    tags = [
        _tags.InternalLinkOrCategoryTag(),
        _tags.ExternalLinkTag(),
        _tags.BoldTextTag(),
        _tags.ItalicTextTag(),
        _tags.UnderlinedTextTag(),
        _tags.StrikethroughTextTag(),
        _tags.OverlinedTextTag(),
        _tags.FileTag(),
    ]
    return {t.open_delimiter: t for t in tags}


# TODO nowiki, noinclude, includeonly, onlyinclude tags
class WikicodeParser:
    """
    The parser’s role is to convert wikicode into a token tree
    to be used by skins to render pages, to categories pages, etc.
    """
    # TODO use titles’ regex
    REDIRECT_PATTERN = re.compile(r'@REDIRECT\[\[([^\n]+?)(?:#([^\n]+?))?]]')
    MAX_TRANSCLUSIONS_DEPTH = 50  # TODO change after tests

    # States
    TEXT = 'text'
    SPECIAL_TAG = 'special_tag'
    HTML_TAG = 'html_tag'
    DELIMITER = 'delimiter'

    # TODO disable all on* attributes
    ALLOWED_HTML_TAGS = (
        ('abbr', False),
        ('address', False),
        ('area', True),
        ('article', False),
        ('aside', False),
        ('b', False),
        ('bdi', False),
        ('bdo', False),
        ('blockquote', False),
        ('br', True),
        ('button', False),
        ('canvas', False),
        ('cite', False),
        ('code', False),
        ('data', False),
        ('dd', False),
        ('del', False),
        ('details', False),
        ('dfn', False),
        ('div', False),
        ('dl', False),
        ('dt', False),
        ('em', False),
        ('footer', False),
        ('header', False),
        ('hr', True),
        ('i', False),
        ('ins', False),
        ('kbd', False),
        ('label', False),
        ('li', False),
        ('main', False),
        ('map', False),
        ('mark', False),
        ('meter', False),
        ('nav', False),
        ('noscript', False),
        ('ol', False),
        ('output', False),
        ('p', False),
        ('pre', False),
        ('progress', False),
        ('q', False),
        ('rp', False),
        ('rt', False),
        ('ruby', False),
        ('s', False),
        ('samp', False),
        ('section', False),
        ('small', False),
        ('span', False),
        ('strong', False),
        ('sub', False),
        ('summary', False),
        ('sup', False),
        ('time', False),
        ('u', False),
        ('ul', False),
        ('var', False),
        ('wbr', False),
    )
    """
    The list of every allowed HTML tag.
    The boolean in each tuple indicates whether the tag has a closing tag.
    """

    __magic_keywords: typ.Dict[str, _registry.MagicKeyword] = {}
    __special_tags: typ.Dict[str, _tags.NonHTMLTag] = _init_special_tags()
    __html_tags: typ.Dict[str, _tags.ExtendedHTMLTag] = {}  # TODO add extension ID
    __functions: typ.Dict[str, _registry.ParserFunction] = {}

    def __init__(self):
        self.__max_depth_reached = False
        self.__too_many_redirects = False
        self.__circular_transclusion = False
        self.__called_non_existant_template = False
        self.__delimiters_starts = {t.open_delimiter[0] for t in self.__special_tags.values()}
        self.__placeholders = {}
        self.__categories = {}  # TODO

    @property
    def max_depth_reached(self) -> bool:
        """Whether the maximum recursion depth has been reached while parsing the code."""
        return self.__max_depth_reached

    @property
    def too_many_redirects(self) -> bool:
        """Whether the redirection limit has been reached while parsing the code."""
        return self.__too_many_redirects

    @property
    def circular_transclusion_detected(self) -> bool:
        """Whether a circular transclusion has been detected while parsing the code."""
        return self.__circular_transclusion

    @property
    def called_non_existant_template(self) -> bool:
        """Whether there was an attempt to transclude a non-existant template."""
        return self.__called_non_existant_template

    @property
    def categories(self) -> typ.Dict[str, str]:
        """The list of categories with their sort key that where encountered while parsing."""
        return dict(self.__categories)

    def parse_wikicode(self, wikicode: str, context, no_redirect: bool = False) \
            -> typ.Union[_nodes.DocumentNode, _nodes.RedirectNode]:
        """
        Parses the given wikicode.

        :param wikicode: The wikicode to parse.
        :param context: The page context to use.
        :type context: WikiPy.page_context.PageContext
        :param no_redirect: If true and the wikicode is a redirection, this redirection will not be followed and a
                            RedirectNode will be returned instead.
        :return: The parsed wikicode as a DocumentNode or RedirectNode.
        """
        return self._parse_wikicode_impl(wikicode, context, 0, no_redirect, {})

    def _parse_wikicode_impl(self, wikicode: str, context, depth: int, no_redirect: bool,
                             variables_values: typ.Dict[str, str]) \
            -> typ.Union[_nodes.DocumentNode, _nodes.RedirectNode]:
        """
        Parses the given wikicode recursively.

        :param wikicode: The wikicode to parse.
        :param context: The context to use.
        :type context: WikiPy.page_context.PageContext
        :param depth: The current recursive parsing depth. If it is greater than the defined limit,
            the parsing stops for the current branch and a DocumentNode containing the raw text is returned.
        :param no_redirect: If true and the wikicode is a redirection, this redirection will not be followed and a
            RedirectNode will be returned instead.
        :param variables_values: A dictionary mapping variables to their respective value.
        :return: The parsed wikicode as a DocumentNode or RedirectNode.
        """
        from ..api import titles as api_titles, pages as api_pages

        wikicode = wikicode.strip()

        # Maximum depth reached, stop parsing
        if depth > self.MAX_TRANSCLUSIONS_DEPTH:
            self.__max_depth_reached = True
            return _nodes.DocumentNode(_nodes.ParagraphNode(_nodes.TextNode(text=self.make_safe(wikicode))))

        if redirect := self.get_redirect(wikicode):
            page_title, anchor = redirect
            if no_redirect:
                root_node = _nodes.RedirectNode(target_page=page_title, anchor=anchor)
            else:
                ns, title = api_titles.extract_namespace_and_title(page_title, ns_as_id=True)
                revision = api_pages.get_page_revision(ns, title, performer=context.user)
                if revision:
                    root_node = self._parse_wikicode_impl(revision.content, context, depth + 1, no_redirect=False,
                                                          variables_values=variables_values)
                else:
                    root_node = _nodes.DocumentNode(
                        _nodes.ParagraphNode(_nodes.TextNode(text=self.make_safe(wikicode))))
        else:
            wikicode = self._substitute_and_transclude(wikicode, context, depth, variables_values)
            wikicode = self._substitute_functions(wikicode)
            wikicode = wikicode.replace('{{!}}', '|')  # Substitute '|' placeholders
            root_node = _nodes.DocumentNode(*self._parse_document(wikicode, top=depth == 0))

        return root_node

    def _substitute_and_transclude(self, wikicode: str, context, depth: int, variables_values: typ.Dict[str, str]) \
            -> str:
        """
        Performs the following operations in this order:
            - substitutes magic keywords
            - substitutes variables with their value
            - transcludes templates and other pages

        :param wikicode: The wikicode to preform these operations on.
        :param context: The page context to use.
        :type context: WikiPy.page_context.PageContext
        :param depth: The current recursive parsing depth.
        :param variables_values: A dictionary mapping variables to their respective values.
        :return: The substituted wikicode.
        """
        wikicode = self._substitute_magic_keywords(wikicode, context)
        wikicode = self._substitute_variables(wikicode, variables_values)
        return self._perform_transclusions(wikicode, context, depth)

    def _substitute_magic_keywords(self, wikicode: str, context) -> str:
        """
        Substitutes magic keywords with their value.

        :param wikicode: The wikicode to perform substitutions on.
        :param context: The context to use.
        :type context: WikiPy.page_context.PageContext
        :return: The substituted wikicode.
        """
        for name, mk in self.__magic_keywords.items():
            token = f'{{{{{name}}}}}'
            if token in wikicode:
                wikicode = wikicode.replace(token, mk(context) if mk.takes_context else mk())
        return wikicode

    def _substitute_variables(self, wikicode: str, variables_values: typ.Dict[str, str], depth: int = 0) -> str:
        """
        Recursively substitutes variables with their values.

        :param wikicode: The wikicode to perform substitutions on.
        :param variables_values: A dictionary mapping variables to their respective values.
        :param depth: The current recursive parsing depth.
        :return: The substituted wikicode.
        """
        # Maximum depth reached, stop parsing
        if depth > self.MAX_TRANSCLUSIONS_DEPTH:
            self.__max_depth_reached = True
            return wikicode

        open_delimiter = '{['
        close_delimiter = ']}'
        result = ''
        buffer = ''
        in_variable = False
        in_name = False
        var_name = ''
        default_value = ''
        # Number of times the variable opening delimiter has been encountered
        opened_tags = 0
        i = 0

        while i < len(wikicode):
            c = wikicode[i]
            next_c = wikicode[i + 1] if i < len(wikicode) - 1 else ''
            open_del = c + next_c == open_delimiter
            close_del = c + next_c == close_delimiter

            if not in_variable:
                if open_del:
                    result += buffer
                    in_variable = True
                    in_name = True
                    opened_tags += 1
                    var_name = ''
                    default_value = ''
                    buffer = ''
                    i += 1
                else:
                    buffer += c

            elif in_name:
                if re.match(r'[ \w.-]', c):
                    var_name += c
                elif c == '|' or close_del:
                    in_name = False
                    if close_del:
                        in_variable = False
                        result += variables_values.get(var_name.strip(), open_delimiter + var_name + close_delimiter)
                        opened_tags -= 1
                        i += 1
                else:
                    buffer += open_delimiter + var_name
                    in_variable = False
                    in_name = False
                    opened_tags -= 1
                    i -= 1  # Step back to not skip current character, it may be part of a tag opening

            else:
                if open_del:
                    opened_tags += 1
                    default_value += c + next_c
                    i += 1
                elif close_del:
                    opened_tags -= 1
                    if opened_tags == 0:
                        result += variables_values.get(
                            var_name.strip(),
                            self._substitute_variables(default_value.strip(), variables_values, depth=depth + 1)
                        )
                        default_value = ''
                        in_variable = False
                        i += 1
                    else:
                        default_value += c
                else:
                    default_value += c

            i += 1
        if in_variable:
            buffer += open_delimiter + var_name
            if not in_name:
                buffer += '|' + variables_values.get(
                    var_name.strip(),
                    self._substitute_variables(default_value.strip(), variables_values, depth=depth + 1)
                )

        return result + buffer

    def _perform_transclusions(self, wikicode: str, context, depth: int) -> str:
        """
        Recursively performs all transclusions on the given wikicode.

        :param wikicode: The wikicode to perform substitutions on.
        :param context: The context to use.
        :type context: WikiPy.page_context.PageContext
        :param depth: The current recursive parsing depth.
        :return: The wikicode with all transclusions performed.
        """
        # Maximum depth reached, stop parsing
        if depth > self.MAX_TRANSCLUSIONS_DEPTH:
            self.__max_depth_reached = True
            return wikicode

        from ..api import titles as api_titles, pages as api_pages
        from .. import settings

        def transclude():
            redirects_depth = 0
            current_template_name = template_name
            while redirects_depth <= settings.MAX_REDIRECTS_DEPTH:
                ns_id, title = api_titles.extract_namespace_and_title(current_template_name, ns_as_id=True)
                if ns_id == settings.MAIN_NS.id and not current_template_name.strip().startswith(':'):
                    full_title = api_titles.get_full_page_title(settings.TEMPLATE_NS.id, title)
                else:
                    full_title = api_titles.get_full_page_title(ns_id, title)
                ns_id, title = api_titles.extract_namespace_and_title(
                    api_titles.get_actual_page_title(api_titles.title_from_url(full_title)),
                    ns_as_id=True
                )

                if ns_id == context.page.namespace_id and title == context.page.title:
                    self.__circular_transclusion = True
                    text = context.language.translate('parser.error.circular_transclusion')
                    return self._generate_placeholder(
                        'error',
                        f'<span class="wpy-parser-error wpy-circular-transclusion">{text}</span>'
                    )

                revision = api_pages.get_page_revision(ns_id, title, performer=context.user)
                if revision:
                    redirect = self.get_redirect(revision.content)
                    if redirect:
                        current_template_name = redirect[0]
                        redirects_depth += 1
                    else:
                        return self._substitute_and_transclude(revision.content, context, depth + 1,
                                                               variables_values={k.strip(): v.strip() for k, v in
                                                                                 params_values.items()})
                else:
                    self.__called_non_existant_template = True
                    return f'[[{api_titles.get_namespace_name(ns_id)}:{title}]]'

            self.__too_many_redirects = True
            text = context.language.translate('parser.error.too_many_redirects', template_name=template_name)
            return self._generate_placeholder(
                'error',
                f'<span class="wpy-parser-error wpy-too-many-redirects">{text}</span>'
            )

        open_delimiter = '{{'
        close_delimiter = '}}'
        result = ''
        buffer = ''
        in_template = False
        in_name = False
        in_param_name = False
        in_param_value = False
        template_name = ''
        param_index = 1
        param_name = ''
        param_value = ''
        params_values = {}
        opened_tags = 0
        i = 0

        while i < len(wikicode):
            c = wikicode[i]
            next_c = wikicode[i + 1] if i < len(wikicode) - 1 else ''
            open_del = c + next_c == open_delimiter
            close_del = c + next_c == close_delimiter

            if not in_template:
                if open_del:
                    result += buffer
                    in_template = True
                    in_name = True
                    template_name = ''
                    param_index = 1
                    param_name = ''
                    param_value = ''
                    params_values = {}
                    buffer = ''
                    i += 1
                else:
                    buffer += c

            elif in_name:
                if re.match(r'[\s\w:.-]', c):
                    template_name += c
                elif c == '|' or close_del:
                    in_name = False
                    if close_del:
                        in_template = False
                        result += transclude()
                        i += 1
                    else:
                        in_param_name = True
                        param_name = ''
                        param_value = ''
                else:
                    buffer += open_delimiter + template_name
                    in_template = False
                    in_name = False
                    i -= 1  # Step back to not skip current character, it may be part of a tag opening

            elif in_param_name:
                if re.match(r'[\s\w.-]', c):
                    param_name += c
                elif c == '=':
                    if param_name.strip() == '':
                        param_value = param_name + '='
                        param_name = str(param_index)
                        param_index += 1
                    in_param_name = False
                    in_param_value = True
                elif c == '|' or close_del:
                    # Positional parameter, param_name contains the actual value
                    params_values[str(param_index)] = param_name
                    if close_del:
                        in_template = False
                        in_param_name = False
                        result += transclude()
                        i += 1
                        buffer = ''
                    else:
                        param_name = ''
                        param_index += 1
                elif open_del:
                    opened_tags += 1
                    in_param_name = False
                    in_param_value = True
                    param_value = param_name + c + next_c
                    param_name = str(param_index)
                    param_index += 1
                    i += 1
                else:
                    in_param_name = False
                    in_param_value = True
                    param_value = param_name

            elif in_param_value:
                if opened_tags > 0:
                    if close_del:
                        opened_tags -= 1
                        param_value += c + next_c
                        i += 1
                    elif open_del:
                        opened_tags += 1
                        param_value += c + next_c
                        i += 1
                    else:
                        param_value += c
                elif c == '|' or close_del:
                    params_values[param_name] = param_value
                    in_param_value = False
                    if close_del:
                        in_template = False
                        result += transclude()
                        i += 1
                        buffer = ''
                    else:
                        in_param_name = True
                        param_name = ''
                        param_value = ''
                elif open_del:
                    opened_tags += 1
                    param_value += c + next_c
                    i += 1
                else:
                    param_value += c

            i += 1
        if in_template:
            buffer += open_delimiter + template_name
            if param_name:
                params_values[param_name] = param_value
            if params_values:
                def subst(item):
                    if not item[0].strip().isdigit():
                        key = (item[0] + '=')
                    else:
                        key = ''
                    return key + self._perform_transclusions(item[1], context, depth)

                buffer += '|' + '|'.join(map(subst, params_values.items()))

        return result + buffer

    # noinspection PyMethodMayBeStatic
    def _substitute_functions(self, wikicode: str) -> str:
        """
        Substitutes all parser functions.

        :param wikicode: The wikicode to perform substitutions on.
        :return: The substituted wikicode.
        """
        return wikicode  # TODO

    def _parse_document(self, wikicode: str, top: bool = False) -> typ.Sequence[_nodes.WikicodeNode]:
        """
        Converts the wiki code into a sequence of nodes.

        :param wikicode: The wikicode to parse.
        :param top: Indicates whether the given wikicode is at the root document.
            If true, all placeholders will be substituted with their value.
        :return: A sequence of nodes.
        """

        def new_paragraph(b: str):
            nonlocal paragraph

            if b.strip():
                paragraph.append(_nodes.TextNode(text=b))
            if not paragraph.is_empty:
                nodes.append(paragraph)
                paragraph = _nodes.ParagraphNode()

        wikicode = self.make_safe(wikicode)  # TEMP remove once HTML tags are correctly parsed

        if top:
            # Tags should be already parsed at this point,
            # we can safely re-insert placeholders (except nowikis)
            wikicode = self._substitute_placeholders(wikicode)

        state = self.TEXT
        tag = None
        nodes = []
        paragraph = _nodes.ParagraphNode()
        buffer = ''
        # Number of times the current delimiter has been encountered for the current tag
        opened_tags = 0
        i = 0

        while i < len(wikicode):
            c = wikicode[i]
            next_c = wikicode[i + 1] if i < len(wikicode) - 1 else ''

            if state == self.TEXT:
                if t := self.__special_tags.get(c + next_c):
                    tag = t
                    opened_tags = 1
                    if buffer:
                        paragraph.append(_nodes.TextNode(text=buffer))
                        buffer = ''
                    state = self.SPECIAL_TAG
                    i += 1
                elif c + next_c == '\n\n':
                    new_paragraph(buffer)
                    buffer = ''
                    i += 1
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
                        if node.content_to_parse is not None:
                            internal_nodes = self._parse_document(node.content_to_parse)
                            if tag.multiline:
                                node.set_parsed_content_nodes(internal_nodes)
                            elif len(internal_nodes) != 0:
                                # noinspection PyUnresolvedReferences
                                node.set_parsed_content_nodes(internal_nodes[0].nodes)
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

        if top:
            for node in nodes:
                node.substitute_placeholders(self.__placeholders)
                self.__categories.update({
                    category_node.title: category_node.sort_key
                    for category_node in node.get_categories()
                })

        print('Parser nodes:', nodes)  # DEBUG

        return nodes

    def _generate_placeholder(self, name: str, content: str) -> str:
        """
        Generates a new placeholder with the given name and content.
        The generated placeholder and its associated content are then
        stored into the placeholders registry.

        :param name: The name to insert into this placeholder.
        :param content: The content this placeholder replaces.
        :return: The generated placeholder.
        """
        n = random.randint(0, 0xffffffff)
        placeholder = f"""?#`″PLACEHOLDER--{name}-{hex(n)[2:].rjust(8, '0').upper()}--REDLOHECALP″`#?"""
        self.__placeholders[placeholder] = content
        return placeholder

    def _substitute_placeholders(self, text: str) -> str:
        """
        Substitutes all placeholders (except nowiki) in the given text by using the placeholders registry.

        :param text: The text.
        :return: The text with all placeholders substituted.
        """
        for ph, subst in self.__placeholders.items():
            if ph in text and 'nowiki' not in ph:
                text = text.replace(ph, subst)
        return text

    @classmethod
    def _register_tag(cls, tag: _tags.ExtendedHTMLTag):
        """
        Registers a custom HTML-like tag.

        :param tag: The tag to register.
        :raises ValueError: If a tag with the same name is already registered.
        """
        if tag.name in cls.__html_tags:
            raise ValueError(f'attempt to register two tags with the same name "{tag.name}"')
        cls.__html_tags[tag.name] = tag

    @classmethod
    def registered_tags(cls) -> typ.List[_tags.ExtendedHTMLTag]:
        """Returns the list of all registered custom HTML-like tags."""
        return sorted(cls.__html_tags.values(), key=lambda t: t.name)

    @classmethod
    def _register_magic_keyword(cls, mk: _registry.MagicKeyword):
        """
        Registers a magic keyword.

        :param mk: The keyword to register.
        :raises ValueError: If a keyword with the same name is already registered.
        """
        if mk.name in cls.__magic_keywords:
            raise ValueError(f'attempt to register two magic keywords with the same name "{mk.name}"')
        cls.__magic_keywords[mk.name] = mk

    @classmethod
    def registered_magic_keywords(cls) -> typ.List[_registry.MagicKeyword]:
        """Returns the list of all registered magic keywords."""
        return sorted(cls.__magic_keywords.values(), key=lambda mk: mk.name)

    @classmethod
    def _register_function(cls, function: _registry.ParserFunction, name: str):
        """
        Registers a parser function.

        :param function: The function to register.
        :raises ValueError: If a function with the same name is already registered.
        """
        if name in cls.__functions:
            raise ValueError(f'attempt to register two functions with the same name "{name}"')
        cls.__functions[name] = function

    @classmethod
    def registered_functions(cls) -> typ.List[_registry.ParserFunction]:
        """Returns the list of all registered parser functions."""
        return sorted(cls.__functions.values(), key=lambda f: f.name)

    @staticmethod
    def make_safe(text: str) -> str:
        """
        Makes the given text safe by escaping all "<" and ">" characters.

        :param text: The text to escape.
        :return: The safe text.
        """
        return text.replace('<', '&lt;').replace('>', '&gt;')

    @classmethod
    def get_redirect(cls, wikicode: str) -> typ.Optional[typ.Tuple[str, typ.Optional[str]]]:
        """
        If the given wikicode is a redirection, returns the target page’s full title and anchor.

        :param wikicode: The wikicode to parse.
        :return: A tuple containing the full title and anchor, or None if the wikicode is not a redirection.
        """
        from ..api import titles as api_titles, errors as api_errors

        if m := cls.REDIRECT_PATTERN.fullmatch(wikicode.strip()):
            title = m.group(1)
            anchor = m.group(2) if m.lastindex == 2 else None
            try:
                api_titles.check_title(title)
            except (api_errors.BadTitleError, api_errors.EmptyPageTitleError):
                pass
            else:
                return api_titles.get_actual_page_title(title), anchor
        return None

    # TODO
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


__all__ = [
    'WikicodeParser',
    'WikicodeNode',
    'RedirectNode',
    'ExtendedHTMLTagNode',
    'ExtendedHTMLTag',
    'load_magic_keywords',
    'load_functions',
    'magic_keyword',
    'parser_function',
    'get_registered_magic_keywords',
    'get_registered_functions',
    'ParserFeature',
    'ParserFunction',
    'MagicKeyword',
]
