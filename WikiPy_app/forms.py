import typing as typ

import django.contrib.auth as dj_auth
import django.forms as dj_forms

from . import api, settings


def _init_namespace_choices(add_all: bool) -> typ.Iterable[typ.Tuple[str, str]]:
    choices = []

    if add_all:
        choices.append(('', ''))

    for ns_id, ns in settings.NAMESPACES.items():
        if ns_id != settings.SPECIAL_NS.id:
            choices.append((str(ns_id), ns.get_name(local=True)))

    def sort(t):
        k = t[0]
        if k == '':  # "All" is first
            return -1_000_000
        k = int(k)
        if k < 0:  # Negative namespaces at the end
            return 1_000_000 - 1 / k
        return k

    return sorted(choices, key=sort)


def _init_language_choices() -> typ.Iterable[typ.Tuple[str, str]]:
    choices = []

    for code, language in settings.i18n.get_languages().items():
        choices.append((code, f'{code} - {language.name}'))

    return sorted(choices)


class WikiPyForm(dj_forms.Form):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__name = name

        for visible in self.visible_fields():
            if isinstance(visible.field.widget, dj_forms.CheckboxInput):
                visible.field.widget.attrs['class'] = 'form-check-input'
            else:
                visible.field.widget.attrs['class'] = 'form-control'

        for field_name, field in self.fields.items():
            field.widget.attrs['id'] = f'wpy-{self.__name}-form-' + field_name.replace('_', '-')

    @property
    def name(self):
        return self.__name


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


class LogInForm(SupportsReturnTo):
    username = dj_forms.CharField(
        label='username',
        required=True,
        help_text=True,
        validators=[api.log_in_username_validator]
    )
    password = dj_forms.CharField(
        label='password',
        required=True,
        help_text=True,
        widget=dj_forms.PasswordInput()
    )

    def __init__(self, *args, **kwargs):
        super().__init__('login', *args, **kwargs)


class SignUpForm(SupportsReturnTo, ConfirmPasswordForm):
    # noinspection PyProtectedMember
    username = dj_forms.CharField(
        label='username',
        min_length=1,
        max_length=dj_auth.get_user_model()._meta.get_field('username').max_length,
        help_text=True,
        validators=[api.username_validator],
        required=True
    )
    email = dj_forms.CharField(
        label='email',
        help_text=True,
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api.email_validator]
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
        super().__init__('create-account', *args, **kwargs)


class ContributionsForm(WikiPyForm):
    target_user = dj_forms.CharField(
        label='target_user',
        required=True,
        validators=[api.log_in_username_validator]
    )
    namespace = dj_forms.ChoiceField(
        choices=_init_namespace_choices(add_all=True),
        label='namespace',
        required=False
    )
    from_date = dj_forms.DateField(
        label='from',
        required=False,
        widget=dj_forms.TextInput(attrs={'type': 'date'})
    )
    to_date = dj_forms.DateField(
        label='to',
        required=False,
        widget=dj_forms.TextInput(attrs={'type': 'date'})
    )
    only_hidden_revisions = dj_forms.BooleanField(
        label='only_hidden_revisions',
        required=False
    )
    only_last_edits = dj_forms.BooleanField(
        label='only_last_edits',
        required=False
    )
    only_page_creations = dj_forms.BooleanField(
        label='only_page_creations',
        required=False
    )
    hide_minor = dj_forms.BooleanField(
        label='hide_minor',
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__('contribs', *args, **kwargs)


class PreferencesForm(WikiPyForm):
    prefered_language = dj_forms.ChoiceField(
        choices=_init_language_choices(),
        label='prefered_language',
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__('prefs', *args, **kwargs)


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
        required=False,
        disabled=True  # TEMP
    )
    section_id = dj_forms.CharField(
        widget=dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, *args, language: settings.i18n.Language = None, disabled: bool = False, **kwargs):
        super().__init__('edit', *args, **kwargs)

        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True
        if language:
            self.fields['comment'].widget.attrs['placeholder'] = language.translate('form.edit.comment.tooltip')


class SearchPageForm(WikiPyForm):
    query = dj_forms.CharField(
        label='query',
        required=True,
        widget=dj_forms.TextInput(attrs={'type': 'search'})
    )
    namespaces = dj_forms.MultipleChoiceField(
        label='namespaces',
        choices=_init_namespace_choices(add_all=False)
    )

    def __init__(self, *args, **kwargs):
        super().__init__('search', *args, **kwargs)


class SetupPageForm(WikiPyForm, ConfirmPasswordForm):
    # noinspection PyProtectedMember
    username = dj_forms.CharField(
        label='username',
        min_length=1,
        max_length=dj_auth.get_user_model()._meta.get_field('username').max_length,
        help_text=True,
        validators=[api.username_validator],
        required=True
    )
    email = dj_forms.CharField(
        label='email',
        help_text=True,
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api.email_validator]
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
        super().__init__('setup', *args, **kwargs)
