"""
This module defines the default magic keywords.
"""
import datetime

from . import _registry


#########
# Dates #
#########


def _get_datetime(context, user_time: bool) -> datetime:
    """
    Returns the current date and time.

    :param context: The context to use.
    :type context: WikiPy.page_context.PageContext
    :param user_time: If true, the current time in the user’s
        timezone will be returned instead of the server’s timezone.
    :return: The current time in the server’s or user’s timezone.
    """
    if user_time:
        return context.user_date_time
    return context.date_time


# Years


def _get_year(context, user_time: bool) -> str:
    return str(_get_datetime(context, user_time=user_time).year)


@_registry.magic_keyword(takes_context=True)
def user_current_year(context):
    return _get_year(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_year(context):
    return _get_year(context, user_time=False)


# Months


def _get_month(context, user_time: bool, padded: bool) -> str:
    month = str(_get_datetime(context, user_time=user_time).month)
    if padded:
        return month.rjust(2, '0')
    return month


@_registry.magic_keyword(takes_context=True)
def user_current_month(context):
    return _get_month(context, user_time=True, padded=False)


@_registry.magic_keyword(takes_context=True)
def server_current_month(context):
    return _get_month(context, user_time=False, padded=False)


@_registry.magic_keyword(takes_context=True)
def user_current_month_padded(context):
    return _get_month(context, user_time=True, padded=True)


@_registry.magic_keyword(takes_context=True)
def server_current_month_padded(context):
    return _get_month(context, user_time=False, padded=True)


def _get_month_name(context, user_time: bool, abbr: bool) -> str:
    month = _get_datetime(context, user_time=user_time).month
    lang = context.language
    if abbr:
        return lang.get_month_abbreviation(month)
    return lang.get_month_name(month)


@_registry.magic_keyword(takes_context=True)
def user_current_month_name(context):
    return _get_month_name(context, user_time=True, abbr=False)


@_registry.magic_keyword(takes_context=True)
def server_current_month_name(context):
    return _get_month_name(context, user_time=False, abbr=False)


@_registry.magic_keyword(takes_context=True)
def user_current_month_name_abbr(context):
    return _get_month_name(context, user_time=True, abbr=True)


@_registry.magic_keyword(takes_context=True)
def server_current_month_name_abbr(context):
    return _get_month_name(context, user_time=False, abbr=True)


# Days


def _get_day(context, user_time: bool, padded: bool) -> str:
    d = str(_get_datetime(context, user_time=user_time).day)
    if padded:
        return d.rjust(2, '0')
    return d


@_registry.magic_keyword(takes_context=True)
def user_current_day(context):
    return _get_day(context, user_time=True, padded=False)


@_registry.magic_keyword(takes_context=True)
def server_current_day(context):
    return _get_day(context, user_time=False, padded=False)


@_registry.magic_keyword(takes_context=True)
def user_current_day_padded(context):
    return _get_day(context, user_time=True, padded=True)


@_registry.magic_keyword(takes_context=True)
def server_current_day_padded(context):
    return _get_day(context, user_time=False, padded=True)


def _get_day_name(context, user_time: bool, abbr: bool) -> str:
    day = _get_datetime(context, user_time=user_time).weekday()
    lang = context.language
    if abbr:
        return lang.get_day_abbreviation(day)
    return lang.get_day_name(day)


@_registry.magic_keyword(takes_context=True)
def user_current_day_name(context):
    return _get_day_name(context, user_time=True, abbr=False)


@_registry.magic_keyword(takes_context=True)
def server_current_day_name(context):
    return _get_day_name(context, user_time=False, abbr=False)


@_registry.magic_keyword(takes_context=True)
def user_current_day_name_abbr(context):
    return _get_day_name(context, user_time=True, abbr=True)


@_registry.magic_keyword(takes_context=True)
def server_current_day_name_abbr(context):
    return _get_day_name(context, user_time=False, abbr=True)


########
# Time #
########


def _get_time(context, user_time: bool) -> str:
    dt = _get_datetime(context, user_time=user_time)
    return f'{dt.hour:02}:{dt.minute:02}'


@_registry.magic_keyword(takes_context=True)
def user_current_time(context):
    return _get_time(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_time(context):
    return _get_time(context, user_time=False)


# Hours


def _get_hour(context, user_time: bool) -> str:
    return str(_get_datetime(context, user_time=user_time).hour).rjust(2, '0')


@_registry.magic_keyword(takes_context=True)
def user_current_hour(context):
    return _get_hour(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_hour(context):
    return _get_hour(context, user_time=False)


# Minutes


def _get_minute(context, user_time: bool) -> str:
    return str(_get_datetime(context, user_time=user_time).minute).rjust(2, '0')


@_registry.magic_keyword(takes_context=True)
def user_current_minute(context):
    return _get_minute(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_minute(context):
    return _get_minute(context, user_time=False)


# Weeks


def _get_week(context, user_time: bool) -> str:
    return str(_get_datetime(context, user_time=user_time).strftime('%V'))


@_registry.magic_keyword(takes_context=True)
def user_current_week(context):
    return _get_datetime(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_week(context):
    return _get_datetime(context, user_time=False)


# Timestamp


def _get_timestamp(context, user_time: bool) -> str:
    return str(int(_get_datetime(context, user_time=user_time).timestamp()))


@_registry.magic_keyword(takes_context=True)
def user_current_timestamp(context):
    return _get_timestamp(context, user_time=True)


@_registry.magic_keyword(takes_context=True)
def server_current_timestamp(context):
    return _get_timestamp(context, user_time=False)


#################
# Site metadata #
#################


@_registry.magic_keyword(takes_context=True)
def site_name(context):
    return context.project_name


@_registry.magic_keyword(takes_context=True)
def server_name(context):
    return context.request.get_host()


@_registry.magic_keyword
def current_version():
    from .. import settings
    return settings.VERSION


@_registry.magic_keyword(takes_context=True)
def site_lang(context):
    return context.default_language.code


#########
# Pages #
#########


@_registry.magic_keyword(takes_context=True)
def dir_mark(context):
    return '&lrm;' if context.page.content_language.writing_direction == 'ltr' else '&rlm;'


@_registry.magic_keyword(takes_context=True)
def page_id(context):
    if context.page_exists:
        return str(context.page.id)
    return ''


@_registry.magic_keyword(takes_context=True)
def page_language(context):
    if context.page_exists:
        return context.page.content_language.code
    return ''


#############
# Revisions #
#############


def _get_revision_info(context, attr: str, get_attr=str):
    """
    Retrieves the given attribute value of the context’s page revision if it exists.

    :param attr: Name of the attribute to fetch.
    :param get_attr: The function to apply to the revision to get the value to return.
    :type get_attr: typing.Callable[[WikiPy.models.PageRevision], str]
    """
    if hasattr(context, 'revision'):
        return get_attr(getattr(context.revision, attr))
    return ''


@_registry.magic_keyword(takes_context=True)
def revision_id(context):
    return _get_revision_info(context, 'id')


@_registry.magic_keyword(takes_context=True)
def revision_year(context):
    return _get_revision_info(context, 'date', lambda d: str(d.year))


@_registry.magic_keyword(takes_context=True)
def revision_month(context):
    return _get_revision_info(context, 'date', lambda d: str(d.month))


@_registry.magic_keyword(takes_context=True)
def revision_month_padded(context):
    return _get_revision_info(context, 'date', lambda d: str(d.month).rjust(2, '0'))


@_registry.magic_keyword(takes_context=True)
def revision_day(context):
    return _get_revision_info(context, 'date', lambda d: str(d.day))


@_registry.magic_keyword(takes_context=True)
def revision_day_padded(context):
    return _get_revision_info(context, 'date', lambda d: str(d.day).rjust(2, '0'))


@_registry.magic_keyword(takes_context=True)
def revision_timestamp(context):
    return _get_revision_info(context, 'date', lambda d: str(d.timestamp()))


@_registry.magic_keyword(takes_context=True)
def revision_user(context):
    return _get_revision_info(context, 'author', lambda a: a.username)


@_registry.magic_keyword(takes_context=True)
def revision_size(context):
    return _get_revision_info(context, 'diff_size')


@_registry.magic_keyword(takes_context=True)
def namespace_name(context):
    return context.page.namespace.get_name(local=True, gender=context.page_namespace_gender)


@_registry.magic_keyword(takes_context=True)
def namespace_id(context):
    return str(context.page.namespace_id)


@_registry.magic_keyword(takes_context=True)
def full_page_title(context):
    return context.page.full_title


@_registry.magic_keyword(takes_context=True)
def page_title(context):
    return context.page.title


@_registry.magic_keyword(takes_context=True)
def username(context):
    return context.user.username
