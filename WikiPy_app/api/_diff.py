import difflib
import typing as typ

import django.utils.html as dj_html


class Diff:
    def __init__(self, revision1, revision2):
        self.__revision1 = revision1
        self.__revision2 = revision2

    def get(self, escape_html: bool, keep_lines: int):
        content1 = self.__revision1.content.splitlines()
        content2 = self.__revision2.content.splitlines()
        if escape_html:
            content1 = list(map(dj_html.escape, content1))
            content2 = list(map(dj_html.escape, content2))
        diff_gen = list(difflib.ndiff(content1, content2, charjunk=lambda _: False))
        return self.__extract_diff(diff_gen, keep_lines)

    # TODO line numbers
    # TODO keep only N lines before and after each change
    def __extract_diff(self, diff_gen: typ.List[str], keep_lines: int):
        diff = []
        skip = 0
        line_old = 1
        line_new = 1

        for i, line in enumerate(diff_gen):
            if skip:
                skip -= 1
                continue

            if line.startswith('- '):
                if i + 3 < len(diff_gen) and diff_gen[i + 1].startswith('? ') and \
                        diff_gen[i + 2].startswith('+ ') and diff_gen[i + 3].startswith('? '):
                    diff.append((line[2:], diff_gen[i + 2][2:], self.__get_indices(diff_gen[i + 1][2:]),
                                 self.__get_indices(diff_gen[i + 3][2:])))
                    skip = 3
                    line_new += 1
                elif i + 2 < len(diff_gen) and (
                        diff_gen[i + 1].startswith('+ ') and diff_gen[i + 2].startswith('? ')
                        or diff_gen[i + 1].startswith('? ') and diff_gen[i + 2].startswith('+ ')):
                    if diff_gen[i + 1].startswith('? '):
                        diff.append((line[2:], diff_gen[i + 2][2:], self.__get_indices(diff_gen[i + 1][2:]), []))
                    else:
                        diff.append((line[2:], diff_gen[i + 1][2:], [], self.__get_indices(diff_gen[i + 2][2:])))
                    skip = 2
                    line_new += 1
                else:
                    diff.append((line[2:], None, [], []))
                line_old += 1
            elif line.startswith('+ '):
                diff.append((None, line[2:], [], []))
                line_new += 1
            else:
                diff.append((line[2:], line[2:], [], []))
                line_old += 1
                line_new += 1

        return diff

    @staticmethod
    def __get_indices(s: str):
        indices = []
        start = None

        for j, c in enumerate(s):
            if c in '+-^':
                if start is None:
                    start = j
            elif start is not None:
                indices.append((start, j))
                start = None

        return indices
