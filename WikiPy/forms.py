"""
This module defines base form classes and forms used outside of built-in special pages.
"""
import typing as typ

import django.contrib.auth as dj_auth
import django.forms as dj_forms

from . import settings
from .api import users as api_users


def init_namespace_choices(add_all: bool, language: settings.i18n.Language) -> typ.Iterable[typ.Tuple[str, str]]:
    """
    Returns a list of tuples containing all namespaces for choice widgets.
    The "All" option has an the empty string as an ID.

    :param add_all: If true, adds an "All" option at the head of the list.
    :param language: The language to use for the namespaces names.
    :return: A list of tuple, each containing the namespace’s ID and its name in the given language.
    """
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
    """Base class for all forms used by the wiki."""

    def __init__(self, name: str, *args, warn_unsaved_changes: bool = False, **kwargs):
        """
        :param name: This form’s name. It will be used by the I18N framework.
        :param args: Other positional arguments.
        :param warn_unsaved_changes: If true this form will warn the user
            of any unsaved changes before exiting the page.
        :param kwargs: Other named arguments.
        """
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
        """This form’s name."""
        return self.__name

    @property
    def warn_unsaved_changes(self) -> bool:
        """Returns whether this form has to warn the user if they have unsaved changes when exiting the page."""
        return self.__warn_unsaved_changes


class SupportsReturnTo(WikiPyForm):
    """Forms wanting to support the return to action can inherit this class."""
    return_to = dj_forms.CharField(
        label='return_to',
        required=False,
        widget=dj_forms.HiddenInput()
    )


class ConfirmPasswordForm:
    """Forms that need to have password confirmation can inherit this class."""

    def passwords_match(self) -> bool:
        """
        Do the passwords match?
        This method requires the form to have been cleaned and to have a password and password_confirm fields.

        :return: True if the cleaned values in the password and password_confirm fields are the exact same,
            false otherwise.
        """
        cleaned_data = getattr(self, 'cleaned_data')
        return cleaned_data['password'] == cleaned_data['password_confirm']


class EditPageForm(WikiPyForm):
    """Form used when editing a wiki page."""
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
    """ID of the page section being edited (optional)."""

    def __init__(self, *args, language: settings.i18n.Language = None, disabled: bool = False,
                 warn_unsaved_changes=True, **kwargs):
        """
        :param args: Positional arguments.
        :param language: Page’s current language.
        :param disabled: If true, the content field will be disabled.
        :param warn_unsaved_changes: If true this form will warn the user
            of any unsaved changes before exiting the page.
        :param kwargs: Other named arguments.
        """
        super().__init__('edit', *args, warn_unsaved_changes=warn_unsaved_changes, **kwargs)

        if disabled:
            self.fields['content'].widget.attrs['disabled'] = True
        if language:
            self.fields['comment'].widget.attrs['placeholder'] = language.translate('form.edit.comment.tooltip')


class EditMessageForm(WikiPyForm):
    """Form used to create/edit a message."""
    content = dj_forms.CharField(
        label='content',
        required=True,
        help_text=True,
        widget=dj_forms.Textarea(attrs={'rows': 3})
    )
    comment = dj_forms.CharField(
        label='comment',
        required=False
    )
    minor_edit = dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )
    reply_to = dj_forms.IntegerField(
        widget=dj_forms.HiddenInput(),
        required=False
    )
    message_id = dj_forms.IntegerField(
        widget=dj_forms.HiddenInput(),
        required=False
    )

    def __init__(self, *args, name: str = None, language: settings.i18n.Language = None, warn_unsaved_changes=True,
                 **kwargs):
        """
        :param args: Positional arguments.
        :param name: The name of this form. Defaults to 'edit_message'.
        :param language: Page’s current language.
        :param warn_unsaved_changes: If true this form will warn the user
            of any unsaved changes before exiting the page.
        :param kwargs: Other named arguments.
        """
        super().__init__(name or 'edit_message', *args, warn_unsaved_changes=warn_unsaved_changes, **kwargs)

        if language:
            self.fields['comment'].widget.attrs['placeholder'] = language.translate('form.edit.comment.tooltip')


class NewTopicForm(EditMessageForm):
    """Form used to create new topics."""
    title = dj_forms.CharField(
        label='title',
        required=True
    )
    parent_topic = dj_forms.ChoiceField(
        choices=(),
        label='parent_topic',
        required=False
    )

    field_order = ['title', 'parent_topic', 'content', 'comment', 'minor_edit', 'follow_page', 'reply_to', 'message_id']

    def __init__(self, *args, language: settings.i18n.Language = None, warn_unsaved_changes=True, **kwargs):
        """
        :param args: Positional arguments.
        :param language: Page’s current language.
        :param warn_unsaved_changes: If true this form will warn the user
            of any unsaved changes before exiting the page.
        :param kwargs: Other named arguments.
        """
        super().__init__(*args, name='new_topic', language=language, warn_unsaved_changes=warn_unsaved_changes,
                         **kwargs)


class EditTopicForm(WikiPyForm):
    """Form used to edit topics."""
    title = dj_forms.CharField(
        label='title',
        required=True
    )
    comment = dj_forms.CharField(
        label='comment',
        required=False
    )
    minor_edit = dj_forms.BooleanField(
        label='minor_edit',
        required=False
    )

    def __init__(self, *args, language: settings.i18n.Language = None, warn_unsaved_changes=True, **kwargs):
        """
        :param args: Positional arguments.
        :param language: Page’s current language.
        :param warn_unsaved_changes: If true this form will warn the user
            of any unsaved changes before exiting the page.
        :param kwargs: Other named arguments.
        """
        super().__init__('edit_topic', *args, warn_unsaved_changes=warn_unsaved_changes, **kwargs)

        if language:
            self.fields['comment'].widget.attrs['placeholder'] = language.translate('form.edit.comment.tooltip')


class SetupPageForm(WikiPyForm, ConfirmPasswordForm):
    """Form used by the wiki setup page."""
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
