import dataclasses
import difflib
import typing as typ

import django.utils.html as dj_html


@dataclasses.dataclass(frozen=True)
class DiffLine:
    """
    Represents an added, removed or modified line in a diff.

    Attributes
        - line1: The line that was modified in revision 1.
        - line2: The corresponding line in revision 2.
        - range1: Indices between which text was removed in revision 1.
        - range2: Indices between which text was added in revision 2.
    """
    line1: typ.Optional[str]
    line2: typ.Optional[str]
    ranges1: typ.List[typ.Tuple[int, int]]
    ranges2: typ.List[typ.Tuple[int, int]]


DiffType = typ.List[typ.Union[DiffLine, typ.Tuple[int, int]]]
"""
A list of two types of objects:

- A DiffLine object representing a line.
- A tuple containing the number of the first line of the next diff section for each revision.
"""


class Diff:
    def __init__(self, revision1, revision2):
        """
        Creates a lazy diff object for the given revisions.
        The actual difference is computed only when calling the get method.

        :param revision1: First revision.
        :type revision1: WikiPy.models.PageRevision
        :param revision2: Second revision.
        :type revision2: WikiPy.models.PageRevision
        """
        self.__revision1 = revision1
        self.__revision2 = revision2

    def get(self, escape_html: bool, keep_lines: int) -> DiffType:
        """
        Computes the differences between the two revisions.

        :param escape_html: If true, all HTML tags will be escaped in the result.
        :param keep_lines: If true, all unchanged lines will be kept.
        :return: A tuple containing the actual diff, the two revisions and the number of diffs not shown between the two
                 (if the two revisions are from the same page).
        """
        content1 = self.__revision1.content.splitlines()
        content2 = self.__revision2.content.splitlines()
        if escape_html:
            content1 = list(map(dj_html.escape, content1))
            content2 = list(map(dj_html.escape, content2))
        diff_gen = list(difflib.ndiff(content1, content2, charjunk=lambda _: False))  # Keep all characters
        print(diff_gen)
        return self.__extract_diff(diff_gen, keep_lines)

    # TODO line numbers
    # TODO keep only N lines before and after each change
    def __extract_diff(self, diff_gen: typ.List[str], keep_lines: int) -> DiffType:
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
                    diff.append(DiffLine(
                        line1=line[2:],
                        line2=diff_gen[i + 2][2:],
                        ranges1=self.__get_indices(diff_gen[i + 1][2:]),
                        ranges2=self.__get_indices(diff_gen[i + 3][2:])
                    ))
                    skip = 3
                    line_new += 1
                elif i + 2 < len(diff_gen) and (
                        diff_gen[i + 1].startswith('+ ') and diff_gen[i + 2].startswith('? ')
                        or diff_gen[i + 1].startswith('? ') and diff_gen[i + 2].startswith('+ ')):
                    if diff_gen[i + 1].startswith('? '):
                        diff.append(DiffLine(
                            line1=line[2:],
                            line2=diff_gen[i + 2][2:],
                            ranges1=self.__get_indices(diff_gen[i + 1][2:]),
                            ranges2=[]
                        ))
                    else:
                        diff.append(DiffLine(
                            line1=line[2:],
                            line2=diff_gen[i + 1][2:],
                            ranges1=[],
                            ranges2=self.__get_indices(diff_gen[i + 2][2:])
                        ))
                    skip = 2
                    line_new += 1
                else:
                    diff.append(DiffLine(
                        line1=line[2:],
                        line2=None,
                        ranges1=[],
                        ranges2=[]
                    ))
                line_old += 1
            elif line.startswith('+ '):
                diff.append(DiffLine(
                    line1=None,
                    line2=line[2:],
                    ranges1=[],
                    ranges2=[]
                ))
                line_new += 1
            else:
                diff.append(DiffLine(
                    line1=line[2:],
                    line2=line[2:],
                    ranges1=[],
                    ranges2=[]
                ))
                line_old += 1
                line_new += 1

        return diff

    @staticmethod
    def __get_indices(s: str) -> typ.List[typ.Tuple[int, int]]:
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
