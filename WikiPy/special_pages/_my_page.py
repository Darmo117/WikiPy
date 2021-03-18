from . import SpecialPage, REDIRECTIONS_CAT
from .. import page_context, settings

from ..api import titles as api_titles, users as api_users


class MyPage(SpecialPage):
    def __init__(self):
        super().__init__('my_page', 'My page', category=REDIRECTIONS_CAT)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        user = api_users.get_user_from_request(request)
        context = page_context.RedirectPageContext(
            base_context,
            to=api_titles.get_full_page_title(settings.USER_NS.id, user.username)
        )

        return context, [], None


def load_special_page() -> SpecialPage:
    return MyPage()
