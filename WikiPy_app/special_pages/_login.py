import dataclasses
import typing as typ

import django.utils.safestring as dj_safe

from . import SpecialPage, ReturnToPageContext, RedirectPageContext
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class LoginPageContext(page_context.PageContext):
        login_notice: typ.Optional[str]
        login_warning: typ.Optional[str]
        login_error: bool
        login_username: typ.Optional[str]

        def __init__(self, context: page_context.PageContext, /, login_notice: typ.Optional[str],
                     login_warning: typ.Optional[str], login_error: bool,
                     login_username: typ.Optional[str]):
            self._context = context
            self.login_notice = login_notice
            self.login_warning = login_warning
            self.login_error = login_error
            self.login_username = login_username

    class LoginPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'login', 'Login')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            get_params = request.GET
            return_to = api.get_param(get_params, 'return_to')

            context = ReturnToPageContext(base_context, to=return_to)

            if api.get_param(get_params, 'action') == 'login':
                context = self.__login(api, context, request)
            else:
                context = self.__get_disclaimer(api, context, request)

            return context, [], None

        # noinspection PyMethodMayBeStatic
        def __get_disclaimer(self, api, base_context, request) -> LoginPageContext:
            user = api.get_user_from_request(request)

            login_notice = dj_safe.mark_safe(api.render_wikicode(
                api.get_page_content(4, 'Message-LoginDisclaimer')[0],
                base_context.skin_name,
                disable_comment=True
            ))

            if user.is_logged_in:
                login_warning = dj_safe.mark_safe(api.render_wikicode(
                    api.get_page_content(4, 'Message-AlreadyLoggedIn')[0],
                    base_context.skin_name,
                    disable_comment=True
                ))
            else:
                login_warning = None

            return LoginPageContext(base_context, login_notice=login_notice, login_warning=login_warning,
                                    login_error=False, login_username=None)

        def __login(self, api, base_context, request) -> LoginPageContext:
            main_page_title = api.get_full_page_title(
                self._settings.MAIN_PAGE_NAMESPACE_ID,
                self._settings.MAIN_PAGE_TITLE
            )
            post_params = request.POST
            username = api.get_param(post_params, 'wpy-login-username')
            password = api.get_param(post_params, 'wpy-login-password')
            return_to = api.get_param(post_params, 'wpy-login-returnto', default=main_page_title)

            success = api.log_in(request, username, password)

            context = LoginPageContext(base_context, login_notice=None, login_warning=None, login_error=not success,
                                       login_username=username)
            if success and return_to:
                context = RedirectPageContext(context, to=return_to)

            return context

    return LoginPage()
