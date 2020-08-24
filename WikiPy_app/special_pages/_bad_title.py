import dataclasses
import string

import django.utils.safestring as dj_safe

from . import SpecialPage
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class BadTitlePageContext(page_context.PageContext):
        bad_title_message: str

        def __init__(self, context: page_context.PageContext, /, bad_title_message: str):
            self._context = context
            self.bad_title_message = bad_title_message

    class BadTitlePage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'bad_title', 'Bad title')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            notice = string.Template(api.get_page_content(4, 'Message-BadTitle')[0]).safe_substitute(kwargs)
            render = api.render_wikicode(notice, base_context.skin_name)
            context = BadTitlePageContext(base_context, bad_title_message=dj_safe.mark_safe(render))
            return context, [], None

    return BadTitlePage()
