import typing as typ

from . import SpecialPage


def load_special_page(settings) -> SpecialPage:
    class LogoutPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'logout', 'Logout')

        def _get_data_impl(self, api, sub_title, request) \
                -> typ.Tuple[typ.Dict[str, typ.Any], typ.Iterable[typ.Any], typ.Optional[str]]:
            redirect_to = api.get_param(request.GET, 'return_to')

            context = {}
            if redirect_to:
                api.log_out(request)
                context['redirect'] = redirect_to

            user = api.get_user_from_request(request)
            if user.is_logged_in:
                page_title = 'Message-LogoutConfirm'
            else:
                page_title = 'Message-LoggedOut'
            context['wikicode'] = api.get_page_content(4, page_title)

            return context, [], None

    return LogoutPage()
