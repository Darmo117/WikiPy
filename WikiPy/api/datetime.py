"""
This module defines functions to manipulate dates and times.
"""
import datetime

import django.utils.timezone as dj_tz

from .. import models, settings


def now(timezone: datetime.tzinfo = None) -> datetime.datetime:
    """
    Returns the current date in the specified timezone.
    If no timezone is specified, the server’s will be used.

    :param timezone: An optional timezone.
    :return: The current date.
    """
    if timezone:
        return dj_tz.make_naive(dj_tz.now(), timezone)
    return dj_tz.now()


def format_datetime(date_time: datetime.datetime, current_user: models.User, language: settings.i18n.Language,
                    custom_format: str = None) -> str:
    """
    Formats the given date using the given user’s preferences and the given language.
    User’s or specified language’s month and week day names and abbreviations
    will be used for placeholders %a, %A, %b and %B instead of the native Python names.

    See WikiPy.settings.check_datetime_format for more details on date formats.

    :param date_time: The date to format.
    :param current_user: The user to use preferences of.
    :param language: The language to use.
    :param custom_format: If specified, this format will be used instead of the user’s.
    :return: The formatted date.
    """
    if custom_format is not None:
        settings.i18n.check_datetime_format(custom_format)

    weekday = date_time.weekday() + 1  # Monday is 0
    month = date_time.month  # January is 1

    # Translate week day and month tags using current display language and not Python’s locale
    format_string = ((custom_format or current_user.get_datetime_format(language))
                     .replace('%a', language.get_day_abbreviation(weekday).replace('%', '%%'))
                     .replace('%A', language.get_day_name(weekday).replace('%', '%%'))
                     .replace('%b', language.get_month_abbreviation(month).replace('%', '%%'))
                     .replace('%B', language.get_month_name(month).replace('%', '%%')))

    return date_time.strftime(format_string)


__all__ = [
    'now',
    'format_datetime',
]
