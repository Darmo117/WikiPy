import dataclasses
import re
import typing as typ

from . import SpecialPage
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class PageDifferencesPageContext(page_context.PageContext):
        page_diff_error: typ.Optional[str]
        page_diff_diff: typ.Optional[typ.Any]  # FIXME type correctly
        page_diff_revision1: typ.Optional[typ.Any]  # FIXME type correctly
        page_diff_revision2: typ.Optional[typ.Any]  # FIXME type correctly
        page_diff_nb_not_shown: typ.Optional[int]
        page_diff_same_page: typ.Optional[bool]

        def __init__(self, context: page_context.PageContext, /, page_diff_error: str = None,
                     page_diff_diff: typ.Any = None, page_diff_revision1: typ.Any = None,
                     page_diff_revision2: typ.Any = None, page_diff_nb_not_shown: int = None,
                     page_diff_same_page: bool = None):
            self._context = context
            self.page_diff_error = page_diff_error
            self.page_diff_diff = page_diff_diff
            self.page_diff_revision1 = page_diff_revision1
            self.page_diff_revision2 = page_diff_revision2
            self.page_diff_nb_not_shown = page_diff_nb_not_shown
            self.page_diff_same_page = page_diff_same_page

    class PageDifferences(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'page_differences', 'Page differences', has_js=True, has_css=True)

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            if len(sub_title) != 0:
                context, title = self.__get_diff(api, sub_title, base_context, request)
            else:
                context = PageDifferencesPageContext(base_context)
                title = None

            return context, [], title

        def __get_diff(self, api, sub_title, base_context, request):
            user = api.get_user_from_request(request)
            title = None
            error = None
            context = None

            try:
                revision_id1 = int(sub_title[0])
                revision_id2 = int(sub_title[1])
            except ValueError as e:
                m = re.search(r"""(['"])(.*)\1""", str(e))
                error = self._settings.i18n.trans(
                    'special.page_differences.error.invalid_revision_id',
                    revision_id=m.group(2)
                )
            except IndexError:
                error = self._settings.i18n.trans('special.page_differences.error.missing_revision_id')
            else:
                try:
                    diff, revision1, revision2, nb_not_shown = api.get_diff(revision_id1, revision_id2, user, True, 3)

                    if revision1.page.id == revision2.page.id:
                        page_title = api.get_full_page_title(revision1.page.namespace_id, revision1.page.title)
                        title = self._settings.i18n.trans('special.page_differences.title_same_page',
                                                          page_title=page_title)
                    else:
                        page_title1 = api.get_full_page_title(revision1.page.namespace_id, revision1.page.title)
                        page_title2 = api.get_full_page_title(revision2.page.namespace_id, revision2.page.title)
                        title = self._settings.i18n.trans('special.page_differences.title_two_pages',
                                                          page_title1=page_title1, page_title2=page_title2)

                    if (revision1.text_hidden or revision2.text_hidden) and \
                            not user.has_right(self._settings.RIGHT_HIDE_REVISIONS):
                        raise api.PageReadForbidden(None)

                    context = PageDifferencesPageContext(
                        base_context,
                        page_diff_diff=diff,
                        page_diff_revision1=revision1,
                        page_diff_revision2=revision2,
                        page_diff_nb_not_shown=nb_not_shown,
                        page_diff_same_page=revision1.page.id == revision2.page.id
                    )
                except api.RevisionDoesNotExist as e:
                    error = self._settings.i18n.trans(
                        'special.page_differences.error.undefined_revision_id',
                        revision_id=int(str(e))
                    )
                except api.PageReadForbidden:
                    error = self._settings.i18n.trans('special.page_differences.error.read_forbidden')

            if error:
                context = PageDifferencesPageContext(base_context, page_diff_error=error)

            return context, title

    return PageDifferences()
