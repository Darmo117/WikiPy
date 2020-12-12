import dataclasses

from . import SpecialPage, JOURNALS_CAT
from .. import page_context


@dataclasses.dataclass(init=False)
class JournalsPageContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class JournalsPage(SpecialPage):
    def __init__(self):
        super().__init__('journals', 'Journals', category=JOURNALS_CAT, icon='notebook-outline', access_key='j')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = JournalsPageContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return JournalsPage()
