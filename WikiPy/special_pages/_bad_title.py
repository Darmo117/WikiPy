import dataclasses
import string

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context
from ..api import pages as api_pages


@dataclasses.dataclass(init=False)
class BadTitlePageContext(page_context.PageContext):
    bad_title_message: str

    def __init__(self, context: page_context.PageContext, /, bad_title_message: str):
        self._context = context
        self.bad_title_message = bad_title_message


class BadTitlePage(SpecialPage):
    def __init__(self):
        super().__init__('bad_title', 'Bad title')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        text = string.Template(base_context.language.translate('special.bad_title.content')).safe_substitute({
            'invalid_char': kwargs.get('invalid_char')
        }) + '\n\n' + self._get_return_to_main_page_text(base_context.language)
        notice = dj_safe.mark_safe(api_pages.render_wikicode(text, base_context))
        context = BadTitlePageContext(base_context, bad_title_message=dj_safe.mark_safe(notice))

        return context, [], None


def load_special_page() -> SpecialPage:
    return BadTitlePage()
