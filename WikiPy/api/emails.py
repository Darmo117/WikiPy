"""
This module defines functions related to emails.
"""
import typing as typ

import django.core.mail as dj_mail
import django.core.mail.backends.dummy as dj_mail_dummy
import django.utils.crypto as dj_crypto

from . import users, titles
from .. import models, special_pages, settings

_EMAIL_CONNECTION = None


def open_email_connection():
    """Opens the single email connection."""
    global _EMAIL_CONNECTION
    _EMAIL_CONNECTION = dj_mail.get_connection()


def is_email_connection_available() -> bool:
    """
    Tells whether the email connection is open and is not an instance
    of django.core.mail.backends.dummy.EmailBackend.
    """
    return _EMAIL_CONNECTION and not isinstance(_EMAIL_CONNECTION, dj_mail_dummy.EmailBackend)


def generate_email_confirmation_code() -> str:
    """
    Generates a random, unique, secure email confirmation code.

    :return: The code.
    """
    return dj_crypto.get_random_string(length=30)


def send_email_change_confirmation_email(user: models.User, pending_email: str) -> bool:
    """
    Sends an email to the given user to confirm their new email.

    :param user: The user to send the mail to.
    :param pending_email: The email to confirm.
    :return: True if the email was successfully sent, false otherwise.
    """
    user = users.update_user_data(
        user,
        email_pending_confirmation=pending_email,
        performer=None,
        auto=True
    )
    confirmation_code = generate_email_confirmation_code()
    users.update_user_data(user, email_confirmation_code=confirmation_code, performer=None, auto=True)
    link = titles.get_page_url(settings.SPECIAL_NS.id,
                               special_pages.get_special_page_for_id('change_email').get_title(),
                               confirm_code=confirmation_code, user=user.username)
    return send_email(
        user.data.email_pending_confirmation,
        subject=user.prefered_language.translate('email.confirm_email.subject'),
        message=user.prefered_language.translate(
            'email.confirm_email.message',
            username=user.username,
            link=link
        )
    )


def send_email(to: typ.Union[str, models.User], subject: str, message: str) -> bool:
    """
    Sends an email to the given user or email address.

    :param to: The user or email address to send the mail to.
    :param subject: The email’s subject.
    :param message: The email’s content.
    :return: True if the email was successfully sent, false otherwise.
    """
    if hasattr(to, 'django_user'):
        recipient = to.django_user.email
    else:
        recipient = to
    return dj_mail.send_mail(subject, message, from_email=None, recipient_list=[recipient]) != 0


def send_mass_email(recipients: typ.List[models.User], subject: str, message: str) -> int:
    """
    Sends an email to all users in the list.

    :param recipients: The list of users to send the mail to.
    :param subject: The email’s subject.
    :param message: The email’s content.
    :return: The number of emails that were actually sent.
    """
    datatuple = tuple(
        (subject, message, None, [to.django_user.email]) for to in recipients)
    return dj_mail.send_mass_mail(datatuple)


__all__ = [
    'open_email_connection',
    'is_email_connection_available',
    'generate_email_confirmation_code',
    'send_email_change_confirmation_email',
    'send_email',
    'send_mass_email',
]
