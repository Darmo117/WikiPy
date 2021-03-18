import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context
from ..api import pages as api_pages


@dataclasses.dataclass(init=False)
class EmptyTitlePageContext(page_context.PageContext):
    empty_title_message: str

    def __init__(self, context: page_context.PageContext, /, empty_title_message: str):
        self._context = context
        self.empty_title_message = empty_title_message


class EmptyTitlePage(SpecialPage):
    def __init__(self):
        super().__init__('empty_title', 'Empty title')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        text = base_context.language.translate('special.empty_title.content') + '\n\n' \
               + self._get_return_to_main_page_text(base_context.language)
        notice = dj_safe.mark_safe(api_pages.render_wikicode(text, base_context))
        context = EmptyTitlePageContext(base_context, empty_title_message=notice)

        return context, [], None


def load_special_page() -> SpecialPage:
    return EmptyTitlePage()
