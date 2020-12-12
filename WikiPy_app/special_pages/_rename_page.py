import dataclasses

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings


@dataclasses.dataclass(init=False)
class RenamePageContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class RenamePage(SpecialPage):
    def __init__(self):
        super().__init__('rename_page', 'Rename page', category=PAGE_TOOLS_CAT, icon='rename-box', access_key='r',
                         requires_rights=(settings.RIGHT_RENAME_PAGES,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = RenamePageContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return RenamePage()
