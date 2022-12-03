import dataclasses

import django.utils.safestring as dj_safe

from . import SpecialPage, CONNECTION_CAT
from .. import page_context
from ..api import pages as api_pages, users as api_users


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
        context = self._get_return_to_context(request, base_context)

        if context.return_to:
            api_users.log_out(request)
            context = page_context.RedirectPageContext(context, to=context.return_to, is_path=True)
        else:
            user = api_users.get_user_from_request(request)
            if user.is_logged_in:
                page_title = 'LogoutConfirm'
            else:
                page_title = 'LoggedOut'

            logout_notice = dj_safe.mark_safe(api_pages.render_wikicode(
                api_pages.get_message(page_title, performer=context.user)[0],
                base_context
            ))
            context = LogoutPageContext(context, logout_notice=logout_notice)

        return context, [], None


def load_special_page() -> SpecialPage:
    return LogoutPage()
