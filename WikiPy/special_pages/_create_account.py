import dataclasses
import typing as typ

import django.contrib.auth as dj_auth
import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms
import django.utils.safestring as dj_safe

from . import SpecialPage, CONNECTION_CAT
from .. import page_context, forms, settings
from ..api import pages as api_pages, users as api_users, titles as api_titles, errors as api_errors


class SignUpForm(forms.SupportsReturnTo, forms.ConfirmPasswordForm):
    # noinspection PyProtectedMember
    username = dj_forms.CharField(
        label='username',
        max_length=dj_auth.get_user_model()._meta.get_field('username').max_length,
        help_text=True,
        validators=[api_users.username_validator],
        required=True
    )
    email = dj_forms.CharField(
        label='email',
        help_text=True,
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api_users.email_validator]
    )
    # noinspection PyProtectedMember
    password = dj_forms.CharField(
        label='password',
        min_length=1,
        max_length=dj_auth.get_user_model()._meta.get_field('password').max_length,
        help_text=True,
        required=True,
        widget=dj_forms.PasswordInput()
    )
    # noinspection PyProtectedMember
    password_confirm = dj_forms.CharField(
        label='password_confirm',
        min_length=1,
        max_length=dj_auth.get_user_model()._meta.get_field('password').max_length,
        help_text=True,
        required=True,
        widget=dj_forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__('create_account', *args, **kwargs)


@dataclasses.dataclass(init=False)
class CreateAccountPageContext(page_context.PageContext):
    create_account_notice: str
    create_account_form: SignUpForm
    create_account_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, create_account_notice: str,
                 form: SignUpForm = None, global_errors: typ.List[str] = None):
        self._context = context
        self.create_account_notice = create_account_notice
        self.create_account_form = form
        self.create_account_form_global_errors = global_errors


class CreateAccountPage(SpecialPage):
    def __init__(self):
        super().__init__('create_account', 'Create account', category=CONNECTION_CAT, has_form=True)

    def _get_data_impl(self, sub_title, base_context, request, **_):
        context = self._get_return_to_context(request, base_context)

        notice = dj_safe.mark_safe(api_pages.render_wikicode(
            api_pages.get_message('CreateAccountDisclaimer', performer=context.user)[0],
            base_context
        ))

        if request.method == 'POST':
            context = self.__create_account(context, request, notice)
        else:
            context = self.__get_default_context(context, request, notice)

        return context, [], None

    # noinspection PyMethodMayBeStatic
    def __get_default_context(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest, notice: str) \
            -> page_context.PageContext:
        return CreateAccountPageContext(base_context, create_account_notice=notice,
                                        form=SignUpForm(initial=request.GET))

    def __create_account(self, context: page_context.PageContext, request: dj_wsgi.WSGIRequest, notice: str) \
            -> CreateAccountPageContext:
        form = SignUpForm(request.POST)
        errors = []

        if form.is_valid():
            if form.passwords_match():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                email = form.cleaned_data['email']
                try:
                    api_users.create_user(username, password=password, email=email)
                except api_errors.DuplicateUsernameError:
                    errors.append('duplicate_username')
                except api_errors.InvalidUsernameError:
                    errors.append('invalid_username')
                except api_errors.InvalidPasswordError:
                    errors.append('invalid_password')
                except api_errors.InvalidEmailError:
                    errors.append('invalid_email')
                else:
                    main_page_title = api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID,
                                                                     settings.MAIN_PAGE_TITLE)
                    return_to = self._get_return_to_path(form, main_page_title)
                    context = page_context.RedirectPageContext(context, to=return_to)
            else:
                errors.append('passwords_mismatch')

        return CreateAccountPageContext(context, create_account_notice=notice, form=form, global_errors=errors)


def load_special_page() -> SpecialPage:
    return CreateAccountPage()
