import dataclasses
import string

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context, api


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
        notice = string.Template(api.get_message('BadTitle')[0]).safe_substitute(kwargs)
        render = api.render_wikicode(notice, base_context)
        context = BadTitlePageContext(base_context, bad_title_message=dj_safe.mark_safe(render))

        return context, [], None


def load_special_page() -> SpecialPage:
    return BadTitlePage()
