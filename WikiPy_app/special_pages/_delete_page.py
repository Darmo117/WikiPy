import dataclasses

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings


@dataclasses.dataclass(init=False)
class DeletePageContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class DeletePage(SpecialPage):
    def __init__(self):
        super().__init__('delete_page', 'Delete page', category=PAGE_TOOLS_CAT, icon='delete', access_key='d',
                         requires_rights=(settings.RIGHT_DELETE_PAGES,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = DeletePageContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return DeletePage()
