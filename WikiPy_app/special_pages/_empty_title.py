import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class EmptyTitlePageContext(page_context.PageContext):
        empty_title_message: str

        def __init__(self, context: page_context.PageContext, /, empty_title_message: str):
            self._context = context
            self.empty_title_message = empty_title_message

    class EmptyTitlePage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'empty_title', 'Empty title')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            notice = dj_safe.mark_safe(api.render_wikicode(
                api.get_page_content(4, 'Message-EmptyTitle')[0],
                base_context.skin_name
            ))
            context = EmptyTitlePageContext(base_context, empty_title_message=notice)
            return context, [], None

    return EmptyTitlePage()
