from __future__ import annotations

import re
import typing as typ

from . import _errors


class WikicodeParser:
    REDIRECT_PATTERN = re.compile(r'@REDIRECT\[\[([^\n]+?)]]')

    def __init__(self, api):
        self.__api = api

    # TODO
    def parse_wikicode(self, wikicode: str) -> ParsedWikicode:
        # TODO escape unauthorized HTML
        wikicode = wikicode.strip()
        if wikicode:
            wikicode = re.sub(r'\n{2,}', '</p><p>', f'<p>{wikicode}</p>')  # TEMP
        return wikicode

    def get_redirect(self, wikicode: str) -> typ.Optional[str]:
        if m := self.REDIRECT_PATTERN.fullmatch(wikicode.strip()):
            title = m.group(1)
            try:
                self.__api.check_title(title)
                return title
            except (_errors.BadTitleException, _errors.EmptyPageTitleException):
                pass
        return None

    @staticmethod
    def paste_sections(header: str, sections: typ.Dict[int, str]):
        return header + '\n' + '\n'.join(sections.values())

    # TODO
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


class ParsedWikicode:
    # TODO
    pass
