import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage, CONNECTION_CAT
from .. import page_context, api, util


@dataclasses.dataclass(init=False)
class LogoutPageContext(page_context.PageContext):
    logout_notice: str

    def __init__(self, context: page_context.PageContext, /, logout_notice: str):
        self._context = context
        self.logout_notice = logout_notice


class LogoutPage(SpecialPage):
    def __init__(self):
        super().__init__('logout', 'Logout', category=CONNECTION_CAT, icon='logout')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        redirect_to = util.get_param(request.GET, 'return_to')

        context = base_context
        if redirect_to:
            api.log_out(request)
            context = page_context.RedirectPageContext(context, to=redirect_to)

        user = api.get_user_from_request(request)
        if user.is_logged_in:
            page_title = 'LogoutConfirm'
        else:
            page_title = 'LoggedOut'

        logout_notice = dj_safe.mark_safe(api.render_wikicode(
            api.get_message(page_title)[0],
            base_context
        ))
        context = LogoutPageContext(context, logout_notice=logout_notice)

        return context, [], None


def load_special_page() -> SpecialPage:
    return LogoutPage()
