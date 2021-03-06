import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.utils.safestring as dj_safe

from . import SpecialPage, CONNECTION_CAT
from .. import page_context, api, forms, settings


@dataclasses.dataclass(init=False)
class CreateAccountPageContext(page_context.PageContext):
    create_account_notice: str
    create_account_form: forms.SignUpForm
    create_account_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, create_account_notice: str,
                 form: forms.SignUpForm = None, global_errors: typ.List[str] = None):
        self._context = context
        self.create_account_notice = create_account_notice
        self.create_account_form = form
        self.create_account_form_global_errors = global_errors


class CreateAccountPage(SpecialPage):
    def __init__(self):
        super().__init__('create_account', 'Create account', category=CONNECTION_CAT, has_form=True)

    def _get_data_impl(self, sub_title, base_context, request, **_):
        context = self._get_return_to_context(request, base_context)

        notice = dj_safe.mark_safe(api.render_wikicode(
            api.get_message('CreateAccountDisclaimer')[0],
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
                                        form=forms.SignUpForm(initial=request.GET))

    def __create_account(self, context: page_context.PageContext, request: dj_wsgi.WSGIRequest, notice: str) \
            -> CreateAccountPageContext:
        form = forms.SignUpForm(request.POST)
        errors = []

        if form.is_valid():
            if form.passwords_match():
                username = form.cleaned_data['username']
                password = form.cleaned_data['password']
                email = form.cleaned_data['email']
                try:
                    api.create_user(username, password=password, email=email)
                except api.DuplicateUsernameError:
                    errors.append('duplicate_username')
                else:
                    main_page_title = api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
                    return_to = self._get_return_to_path(form, main_page_title)
                    context = page_context.RedirectPageContext(context, to=return_to)
            else:
                errors.append('passwords_mismatch')

        return CreateAccountPageContext(context, create_account_notice=notice, form=form, global_errors=errors)


def load_special_page() -> SpecialPage:
    return CreateAccountPage()
