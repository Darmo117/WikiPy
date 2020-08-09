import typing as typ

from . import SpecialPage


def load_special_page(settings) -> SpecialPage:
    class LoginPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'login', 'Login')

        def _get_data_impl(self, api, sub_title, request) \
                -> typ.Tuple[typ.Dict[str, typ.Any], typ.Iterable[typ.Any], typ.Optional[str]]:
            get_params = request.GET
            redirect_to = api.get_param(get_params, 'return_to')

            context = {}
            if redirect_to:
                context['return_to'] = redirect_to

            if api.get_param(get_params, 'action') == 'login':
                main_page_title = api.as_url_title(api.get_full_page_title(
                    self._settings.MAIN_PAGE_NAMESPACE_ID,
                    self._settings.MAIN_PAGE_TITLE
                ))
                post_params = request.POST
                username = api.get_param(post_params, 'wpy-login-username')
                password = api.get_param(post_params, 'wpy-login-password')
                return_to = api.get_param(post_params, 'wpy-login-returnto', default=main_page_title)

                success = api.log_in(request, username, password)

                if success:
                    if return_to:
                        context['redirect'] = api.title_from_url(return_to)
                else:
                    context['login_error'] = True
            else:
                user = api.get_user_from_request(request)
                wikicode = api.get_page_content(4, 'Message-LoginDisclaimer')
                if user.is_logged_in:
                    wikicode += (
                            '<div class="wpy-warning-box">' +
                            api.get_page_content(4, 'Message-AlreadyLoggedIn') +
                            '</div>'
                    )
                context['wikicode'] = wikicode

            return context, [], None

    return LoginPage()
