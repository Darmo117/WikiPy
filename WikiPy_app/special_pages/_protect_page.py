import dataclasses

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings


@dataclasses.dataclass(init=False)
class ProtectPageContext(page_context.PageContext):

    def __init__(self, context: page_context.PageContext, /):
        self._context = context


class ProtectPage(SpecialPage):
    def __init__(self):
        super().__init__('protect_page', 'Protect page', category=PAGE_TOOLS_CAT, icon='shield-edit', access_key='=',
                         requires_rights=(settings.RIGHT_PROTECT_PAGES,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = ProtectPageContext(base_context)

        return context, [], None


def load_special_page() -> SpecialPage:
    return ProtectPage()
