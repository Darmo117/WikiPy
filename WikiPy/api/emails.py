import typing as typ

import django.core.mail as dj_mail
import django.core.mail.backends.dummy as dj_mail_dummy
import django.utils.crypto as dj_crypto

from . import users, titles
from .. import models, special_pages, settings

_EMAIL_CONNECTION = None


def open_email_connection():
    global _EMAIL_CONNECTION
    _EMAIL_CONNECTION = dj_mail.get_connection()


def is_email_connection_available() -> bool:
    return not isinstance(_EMAIL_CONNECTION, dj_mail_dummy.EmailBackend)


def generate_email_confirmation_code() -> str:
    return dj_crypto.get_random_string(length=30)


def send_email_change_confirmation_email(user: models.User, pending_email: str):
    user = users.update_user_data(
        user,
        email_pending_confirmation=pending_email
    )
    confirmation_code = generate_email_confirmation_code()
    users.update_user_data(user, email_confirmation_code=confirmation_code)
    link = titles.get_page_url(settings.SPECIAL_NS.id,
                               special_pages.get_special_page_for_id('change_email').get_title(),
                               confirm_code=confirmation_code, user=user.username)
    send_email(
        user.data.email_pending_confirmation,
        subject=user.prefered_language.translate('email.confirm_email.subject'),
        message=user.prefered_language.translate(
            'email.confirm_email.message',
            username=user.username,
            link=link
        )
    )


def send_email(to: typ.Union[str, models.User], subject: str, message: str):
    if hasattr(to, 'django_user'):
        recipient = to.django_user.email
    else:
        recipient = to
    dj_mail.send_mail(subject, message, from_email=None, recipient_list=[recipient])


def send_mass_email(recipients: typ.List[models.User], subject: str, message: str):
    datatuple = tuple(
        (subject, message, None, [to.django_user.email]) for to in recipients)
    dj_mail.send_mass_mail(datatuple)


__all__ = [
    'open_email_connection',
    'is_email_connection_available',
    'generate_email_confirmation_code',
    'send_email_change_confirmation_email',
    'send_email',
    'send_mass_email',
]
