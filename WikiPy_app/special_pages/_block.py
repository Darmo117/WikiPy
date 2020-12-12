from . import SpecialPage, USERS_AND_RIGHTS_CAT

from .. import settings


class Block(SpecialPage):
    def __init__(self):
        super().__init__('block', 'Block', category=USERS_AND_RIGHTS_CAT, requires_rights=(settings.RIGHT_BLOCK_USERS,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        # TODO
        context = base_context

        return context, [], None


def load_special_page() -> SpecialPage:
    return Block()
