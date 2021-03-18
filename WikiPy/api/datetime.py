import datetime

import django.utils.timezone as dj_tz

from .. import models, settings


def now(timezone: datetime.tzinfo = None) -> datetime.datetime:
    if timezone:
        return dj_tz.make_naive(dj_tz.now(), timezone)
    return dj_tz.now()


def format_datetime(date_time: datetime.datetime, current_user: models.User, language: settings.i18n.Language,
                    custom_format: str = None) -> str:
    weekday = date_time.weekday() + 1  # Monday is 0
    month = date_time.month  # January is 1

    # Translate week day and month tags using current display language and not Python locale
    format_ = (custom_format or current_user.get_datetime_format(language)) \
        .replace('%a', language.get_day_abbreviation(weekday).replace('%', '%%')) \
        .replace('%A', language.get_day_name(weekday).replace('%', '%%')) \
        .replace('%b', language.get_month_abbreviation(month).replace('%', '%%')) \
        .replace('%B', language.get_month_name(month).replace('%', '%%'))
    # Disabled tags
    for tag_name in 'cxX':  # TODO raise exception
        format_ = format_.replace('%' + tag_name, '%%' + tag_name)

    return date_time.strftime(format_)


__all__ = [
    'now',
    'format_datetime',
]
