from . import SpecialPage, RedirectPageContext


def load_special_page(settings) -> SpecialPage:
    class MyPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'my_page', 'My page')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            user = api.get_user_from_request(request)
            context = RedirectPageContext(base_context, to=api.get_full_page_title(6, user.username))
            return context, [], None

    return MyPage()
