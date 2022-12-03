from . import SpecialPage, PAGE_TOOLS_CAT
from .. import settings


class HideRevisions(SpecialPage):
    def __init__(self):
        super().__init__('hide_revisions', 'Hide revisions', category=PAGE_TOOLS_CAT,
                         requires_rights=(settings.RIGHT_DELETE_REVISIONS,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = base_context

        return context, [], None


def load_special_page() -> SpecialPage:
    return HideRevisions()
