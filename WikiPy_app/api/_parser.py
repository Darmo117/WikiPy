from __future__ import annotations
import typing as typ
import re


class WikicodeParser:
    # TODO

    def parse_wikicode(self, wikicode: str) -> ParsedWikicode:
        # TODO
        return wikicode  # TEMP

    @staticmethod
    def paste_sections(header: str, sections: typ.Dict[int, str]):
        return header + '\n' + '\n'.join(sections.values())

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
