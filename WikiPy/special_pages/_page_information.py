import dataclasses

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context


@dataclasses.dataclass(init=False)
class PageInformationContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class PageInformationPage(SpecialPage):
    def __init__(self):
        super().__init__('page_information', 'Page information', category=PAGE_TOOLS_CAT, icon='information-outline',
                         access_key='i')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = PageInformationContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return PageInformationPage()
