import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage, RedirectPageContext
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class LogoutPageContext(page_context.PageContext):
        logout_notice: str

        def __init__(self, context: page_context.PageContext, /, logout_notice: str):
            self._context = context
            self.logout_notice = logout_notice

    class LogoutPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'logout', 'Logout')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            redirect_to = api.get_param(request.GET, 'return_to')

            context = base_context
            if redirect_to:
                api.log_out(request)
                context = RedirectPageContext(context, to=redirect_to)

            user = api.get_user_from_request(request)
            if user.is_logged_in:
                page_title = 'Message-LogoutConfirm'
            else:
                page_title = 'Message-LoggedOut'

            logout_notice = dj_safe.mark_safe(api.render_wikicode(
                api.get_page_content(4, page_title)[0],
                base_context.skin_name,
                disable_comment=True
            ))
            context = LogoutPageContext(context, logout_notice=logout_notice)

            return context, [], None

    return LogoutPage()
