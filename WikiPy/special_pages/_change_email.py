import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, settings, forms
from ..api import users as api_users, titles as api_titles, emails as api_emails, datetime as api_dt


class ChangeEmailForm(forms.WikiPyForm):
    email = dj_forms.CharField(
        label='email',
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api_users.email_validator]
    )

    def __init__(self, *args, **kwargs):
        super().__init__('change_email', *args, **kwargs)


@dataclasses.dataclass(init=False)
class ChangeEmailPageContext(page_context.PageContext):
    change_email_form: ChangeEmailForm
    change_email_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, form: ChangeEmailForm,
                 global_errors: typ.List[str] = None):
        self._context = context
        self.change_email_form = form
        self.change_email_form_global_errors = global_errors


class ChangeEmailPage(SpecialPage):
    def __init__(self):
        super().__init__('change_email', 'Change email', category=USERS_AND_RIGHTS_CAT, has_form=True,
                         requires_logged_in=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        if request.method == 'POST':
            context = self.__change_email(base_context, request)
        elif request.GET.get('confirm_code'):
            context = self.__confirm_email(base_context, request.GET.get('confirm_code'), request.GET.get('user'))
        else:
            context = self.__get_context(base_context)

        return context, [], None

    # noinspection PyMethodMayBeStatic
    def __get_context(self, base_context: page_context.PageContext) -> page_context.PageContext:
        return ChangeEmailPageContext(base_context, form=ChangeEmailForm())

    def __change_email(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest):
        user = api_users.get_user_from_request(request)
        form = ChangeEmailForm(request.POST)

        if form.is_valid():
            new_email = form.cleaned_data['email']
            if new_email != user.django_user.email:
                api_emails.send_email_change_confirmation_email(user, new_email)
                # Reload page
                return page_context.RedirectPageContext(
                    base_context,
                    to=api_titles.get_page_url(settings.SPECIAL_NS.id, self.title, success=1),
                    is_path=True
                )
        return ChangeEmailPageContext(base_context, form=form)

    def __confirm_email(self, base_context: page_context.PageContext, code: str, username: str) \
            -> page_context.PageContext:
        user = api_users.get_user_from_name(username)
        if user and user.data.email_confirmation_code == code:
            user = api_users.update_user_data(
                user,
                email_pending_confirmation=None,
                email_confirmation_code=None,
                email_confirmation_date=api_dt.now(),
                django_email=user.data.email_pending_confirmation,
                performer=None,
                auto=True
            )
            if not user.is_in_group(settings.GROUP_EMAIL_CONFIRMED):
                api_users.add_user_to_group(user, group_id=settings.GROUP_EMAIL_CONFIRMED, performer=None, auto=True)
            # Reload page
            return page_context.RedirectPageContext(
                base_context,
                to=api_titles.get_page_url(settings.SPECIAL_NS.id, self.title, confirm_success=1),
                is_path=True
            )
        else:
            return ChangeEmailPageContext(base_context, form=ChangeEmailForm(), global_errors=['invalid_code'])


def load_special_page() -> SpecialPage:
    return ChangeEmailPage()
