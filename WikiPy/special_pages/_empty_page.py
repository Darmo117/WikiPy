import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage, MISC_CAT
from .. import page_context


@dataclasses.dataclass(init=False)
class EmptyPageContext(page_context.PageContext):
    empty_page_notice: str

    def __init__(self, context: page_context.PageContext, /, empty_page_notice: str):
        self._context = context
        self.empty_page_notice = empty_page_notice


class EmptyPage(SpecialPage):
    def __init__(self):
        super().__init__('empty_page', 'Empty page', category=MISC_CAT)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        notice = dj_safe.mark_safe(base_context.language.translate('special.empty_page.notice'))
        context = EmptyPageContext(base_context, empty_page_notice=notice)

        return context, [], None


def load_special_page() -> SpecialPage:
    return EmptyPage()
