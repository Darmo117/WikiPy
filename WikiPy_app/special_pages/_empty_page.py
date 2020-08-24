import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class EmptyPageContext(page_context.PageContext):
        empty_page_notice: str

        def __init__(self, context: page_context.PageContext, /, empty_page_notice: str):
            self._context = context
            self.empty_page_notice = empty_page_notice

    class EmptyPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'empty_page', 'Empty page')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            notice = dj_safe.mark_safe(self._settings.i18n.trans('special.empty_page.notice'))
            context = EmptyPageContext(base_context, empty_page_notice=notice)
            return context, [], None

    return EmptyPage()
