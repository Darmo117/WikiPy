import dataclasses

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context


@dataclasses.dataclass(init=False)
class LinkedPagesContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class LinkedPagesPage(SpecialPage):
    def __init__(self):
        super().__init__('linked_pages', 'Linked pages', category=PAGE_TOOLS_CAT, icon='link-variant', access_key='l')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = LinkedPagesContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return LinkedPagesPage()
