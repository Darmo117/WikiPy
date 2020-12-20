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


class WikiPyForm(dj_forms.Form):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__name = name

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
    test = dj_forms.BooleanField(
        label='test'
    )
    test2 = dj_forms.ChoiceField(
        choices=((str(i), str(i)) for i in range(10)),
        label='test2',
        widget=dj_forms.RadioSelect
    )
    test3 = dj_forms.ChoiceField(
        choices=((str(i), str(i)) for i in range(10)),
        label='test3'
    )
    test4 = dj_forms.ChoiceField(
        choices=((str(i), str(i)) for i in range(10)),
        label='test4',
        widget=dj_forms.SelectMultiple
    )
    test5 = dj_forms.FileField(
        label='test5'
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


class ChangeEmailForm(WikiPyForm):
    email = dj_forms.CharField(
        label='email',
        required=True,
        widget=dj_forms.EmailInput,
        validators=[api.email_validator]
    )

    def __init__(self, *args, **kwargs):
        super().__init__('change_email', *args, **kwargs)


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
