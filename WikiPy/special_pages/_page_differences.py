import dataclasses
import re
import typing as typ

import django.core.handlers.wsgi as dj_wsgi

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings, api, models
from ..api import pages as api_pages, titles as api_titles, users as api_users, errors as api_errors


@dataclasses.dataclass(init=False)
class PageDifferencesPageContext(page_context.PageContext):
    page_diff_error: typ.Optional[str]
    page_diff_diff: typ.Optional[api.DiffType]
    page_diff_revision1: typ.Optional[models.PageRevision]
    page_diff_revision2: typ.Optional[models.PageRevision]
    page_diff_nb_not_shown: typ.Optional[int]
    page_diff_same_page: typ.Optional[bool]
    page_diff_identical: typ.Optional[bool]

    def __init__(self, context: page_context.PageContext, /, page_diff_error: str = None,
                 page_diff_diff: api.DiffType = None, page_diff_revision1: typ.Any = None,
                 page_diff_revision2: typ.Any = None, page_diff_nb_not_shown: int = None,
                 page_diff_same_page: bool = None, page_diff_identical: bool = None):
        self._context = context
        self.page_diff_error = page_diff_error
        self.page_diff_diff = page_diff_diff
        self.page_diff_revision1 = page_diff_revision1
        self.page_diff_revision2 = page_diff_revision2
        self.page_diff_nb_not_shown = page_diff_nb_not_shown
        self.page_diff_same_page = page_diff_same_page
        self.page_diff_identical = page_diff_identical


class PageDifferences(SpecialPage):
    def __init__(self):
        super().__init__('page_differences', 'Page differences', category=PAGE_TOOLS_CAT, has_js=True, has_css=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        if len(sub_title) != 0:
            context, title = self.__get_diff(sub_title, base_context, request)
        else:
            context = PageDifferencesPageContext(base_context)
            title = None

        return context, [], title

    @staticmethod
    def __get_diff(sub_title: typ.List[str], base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest) \
            -> typ.Tuple[page_context.PageContext, str]:
        user = api_users.get_user_from_request(request)
        title = None
        error = None
        context = None

        try:
            revision_id1 = int(sub_title[0])
            revision_id2 = int(sub_title[1])
        except ValueError as e:
            m = re.search(r"""(['"])(.*)\1""", str(e))
            error = base_context.language.translate(
                'special.page_differences.error.invalid_revision_id',
                revision_id=m.group(2)
            )
        except IndexError:
            error = base_context.language.translate('special.page_differences.error.missing_revision_id')
        else:
            try:
                diff, revision1, revision2, nb_not_shown = api_pages.get_diff(revision_id1, revision_id2, True, 3,
                                                                              performer=user)

                if revision1.page.id == revision2.page.id:
                    page_title = api_titles.get_full_page_title(revision1.page.namespace_id, revision1.page.title)
                    title = base_context.language.translate('special.page_differences.title_same_page',
                                                            page_title=page_title)
                else:
                    page_title1 = api_titles.get_full_page_title(revision1.page.namespace_id, revision1.page.title)
                    page_title2 = api_titles.get_full_page_title(revision2.page.namespace_id, revision2.page.title)
                    title = base_context.language.translate('special.page_differences.title_two_pages',
                                                            page_title1=page_title1, page_title2=page_title2)

                if (revision1.hidden or revision2.hidden) and \
                        not user.has_right(settings.RIGHT_DELETE_REVISIONS):
                    raise api_errors.PageReadForbiddenError(None)

                context = PageDifferencesPageContext(
                    base_context,
                    page_diff_diff=diff,
                    page_diff_revision1=revision1,
                    page_diff_revision2=revision2,
                    page_diff_nb_not_shown=nb_not_shown,
                    page_diff_same_page=revision1.page.id == revision2.page.id
                )
            except api_errors.RevisionDoesNotExistError as e:
                error = base_context.language.translate(
                    'special.page_differences.error.undefined_revision_id',
                    revision_id=int(str(e))
                )
            except api_errors.PageReadForbiddenError:
                error = base_context.language.translate('special.page_differences.error.read_forbidden')

        if error:
            context = PageDifferencesPageContext(base_context, page_diff_error=error)

        return context, title


def load_special_page() -> SpecialPage:
    return PageDifferences()
