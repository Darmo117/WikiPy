import typing as typ

import django.contrib.auth as dj_auth
import django.forms as dj_forms

from . import settings
from .api import users as api_users


def init_namespace_choices(add_all: bool, language: settings.i18n.Language) -> typ.Iterable[typ.Tuple[str, str]]:
    choices = []

    if add_all:
        choices.append(('', language.translate('form.all_namespaces')))

    for ns_id, ns in settings.NAMESPACES.items():
        if ns_id != settings.SPECIAL_NS.id:
            if ns_id == settings.MAIN_NS.id:
                name = f'({language.main_namespace_name})'
            else:
                name = ns.get_name(local=True)
            choices.append((str(ns_id), name))

    def sort(t):
        k = t[0]
        if k == '':  # "All" is first
            return -1_000_000
        k = int(k)
        if k < 0:  # Negative namespaces at the end
            return 1_000_000 - 1 / k
        return k

    return sorted(choices, key=sort)


class WikiPyForm(dj_forms.Form):
    def __init__(self, name: str, *args, warn_unsaved_changes: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.__name = name
        self.__warn_unsaved_changes = warn_unsaved_changes

        for visible in self.visible_fields():
            if isinstance(visible.field.widget, dj_forms.CheckboxInput) or \
                    isinstance(visible.field.widget, dj_forms.RadioSelect) or \
                    isinstance(visible.field.widget, dj_forms.CheckboxSelectMultiple):
                visible.field.widget.attrs['class'] = 'custom-control-input'
            elif isinstance(visible.field.widget, dj_forms.Select):
                visible.field.widget.attrs['class'] = 'custom-select'
            elif isinstance(visible.field.widget, dj_forms.FileInput):
                visible.field.widget.attrs['class'] = 'custom-file-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'

        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = (f'wpy-{self.__name}-form-' + field_name).replace('_', '-')

    @property
    def name(self) -> str:
        return self.__name

    @property
    def warn_unsaved_changes(self) -> bool:
        return self.__warn_unsaved_changes


class SupportsReturnTo(WikiPyForm):
    return_to = dj_forms.CharField(
        label='return_to',
        required=False,
        widget=dj_forms.HiddenInput()
    )


class ConfirmPasswordForm:
    def passwords_match(self) -> bool:
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']


class EditPageForm(WikiPyForm):
    content = dj_forms.CharField(
        label='content',
        required=False,
        widget=dj_forms.Textarea(attrs={'rows': 20})
    )
    comment = dj_forms.CharField(
        label='comment',
        required=False
    )
    minor_edit = dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )
    follow_page = dj_forms.BooleanField(
        label='follow_page',
        required=False
    )
    maintenance_category = dj_forms.BooleanField(
        label='maintenance_category',
        required=False
    )
    section_id = dj_forms.CharField(
        widget=dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, *args, language: settings.i18n.Language = None, disabled: bool = False,
                 warn_unsaved_changes=True, **kwargs):
        super().__init__('edit', *args, warn_unsaved_changes=warn_unsaved_changes, **kwargs)

        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True
        if language:
            self.fields['comment'].widget.attrs['placeholder'] = language.translate('form.edit.comment.tooltip')


class SetupPageForm(WikiPyForm, ConfirmPasswordForm):
    # noinspection PyProtectedMember
    username = dj_forms.CharField(
        label='username',
        min_length=1,
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
    secret_key = dj_forms.CharField(
        label='secret_key',
        help_text=True,
        widget=dj_forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__('setup', *args, warn_unsaved_changes=True, **kwargs)
