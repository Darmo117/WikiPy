import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms
import django.utils.safestring as dj_safe

from . import SpecialPage, CONNECTION_CAT
from .. import page_context, settings, forms
from ..api import pages as api_pages, titles as api_titles, users as api_users


class LogInForm(forms.SupportsReturnTo):
    username = dj_forms.CharField(
        label='username',
        required=True,
        help_text=True,
        validators=[api_users.log_in_username_validator]
    )
    password = dj_forms.CharField(
        label='password',
        required=True,
        help_text=True,
        widget=dj_forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__('login', *args, **kwargs)


@dataclasses.dataclass(init=False)
class LoginPageContext(page_context.PageContext):
    login_notice: str
    login_warning: str
    login_form: LogInForm
    login_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, login_notice: str, login_warning: str = None,
                 form: LogInForm = None, global_errors: typ.List[str] = None):
        self._context = context
        self.login_notice = login_notice
        self.login_warning = login_warning
        self.login_form = form
        self.login_form_global_errors = global_errors


class LoginPage(SpecialPage):
    def __init__(self):
        super().__init__('login', 'Login', category=CONNECTION_CAT, has_form=True, icon='login')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        context = self._get_return_to_context(request, base_context)

        login_notice = dj_safe.mark_safe(api_pages.render_wikicode(
            api_pages.get_message('LoginDisclaimer', performer=context.user)[0],
            base_context
        ))

        if request.method == 'POST':
            context = self.__login(context, request, login_notice)
        else:
            context = self.__get_default_context(context, request, login_notice)

        return context, [], None

    # noinspection PyMethodMayBeStatic
    def __get_default_context(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest,
                              login_notice: str) -> page_context.PageContext:
        user = api_users.get_user_from_request(request)

        if user.is_logged_in:
            login_warning = dj_safe.mark_safe(api_pages.render_wikicode(
                api_pages.get_message('AlreadyLoggedIn', performer=base_context.user)[0],
                base_context
            ))
        else:
            login_warning = None

        return LoginPageContext(base_context, login_notice=login_notice, login_warning=login_warning,
                                form=LogInForm(initial=request.GET))

    def __login(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest, login_notice: str) \
            -> page_context.PageContext:
        return_to = None
        success = False
        errors = []

        form = LogInForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            success = api_users.log_in(request, username, password)
            if success:
                main_page_title = api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID,
                                                                 settings.MAIN_PAGE_TITLE)
                return_to = self._get_return_to_path(form, main_page_title)

        if success and return_to:
            context = page_context.RedirectPageContext(base_context, to=return_to, is_path=True)
        else:
            if not success:
                errors.append('invalid_credentials')
            context = LoginPageContext(base_context, login_notice=login_notice, form=form, global_errors=errors)

        return context


def load_special_page() -> SpecialPage:
    return LoginPage()
