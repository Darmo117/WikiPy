import abc
import datetime
import re

_name_regex = re.compile(r'^\w+$')


class MagicKeyword(abc.ABC):
    def __init__(self, name: str):
        if not re.fullmatch(_name_regex, name):
            raise ValueError(f'invalid magic keyword name "{name}"')
        self.__name = name.upper()

    @property
    def name(self) -> str:
        return self.__name

    @abc.abstractmethod
    def get_value(self, context) -> str:
        """
        Returns the value of this keyword for the given context.

        :param context: The context to use.
        :type context: WikiPy_app.page_context.PageContext
        :return: The value.
        """
        pass


#########
# Dates #
#########


class DateTimeKeyword(MagicKeyword, abc.ABC):
    def __init__(self, name: str, local: bool):
        if local:
            prefix = 'local_'
        else:
            prefix = 'current_'
        super().__init__(prefix + name)
        self._local = local

    def _get_time(self, context) -> datetime:
        if self._local:
            return context.local_date_time
        return context.date_time


class CurrentYearKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('year', local)

    def get_value(self, context):
        return str(self._get_time(context).year)


class CurrentMonthKeyword(DateTimeKeyword):
    def __init__(self, local: bool, padded: bool):
        super().__init__('month' + ('_padded' if padded else ''), local)
        self._padded = padded

    def get_value(self, context):
        s = str(self._get_time(context).month)
        if self._padded:
            return s.ljust(2, '0')
        return s


class CurrentMonthNameKeyword(DateTimeKeyword):
    def __init__(self, local: bool, abbr: bool):
        super().__init__('month_name' + ('_abbr' if abbr else ''), local)
        self._abbr = abbr

    def get_value(self, context):
        m = self._get_time(context).month
        lang = context.default_language
        if self._abbr:
            return lang.get_month_abbreviation(m)
        return lang.get_month_name(m)


class CurrentDayKeyword(DateTimeKeyword):
    def __init__(self, local: bool, padded: bool):
        super().__init__('day' + ('_padded' if padded else ''), local)
        self._padded = padded

    def get_value(self, context):
        s = str(self._get_time(context).day)
        if self._padded:
            return s.ljust(2, '0')
        return s


class CurrentDayOfWeekKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('dow', local)

    def get_value(self, context):
        return str(self._get_time(context).weekday())  # Monday == 0


class CurrentDayNameKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('day_name', local)

    def get_value(self, context):
        return context.default_language.get_day_name(self._get_time(context).weekday())


class CurrentTimeKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('time', local)

    def get_value(self, context):
        h = self._get_time(context).hour
        m = self._get_time(context).minute
        return f'{h:02}:{m:02}'


class CurrentHourKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('hour', local)

    def get_value(self, context):
        return str(self._get_time(context).hour).ljust(2, '0')


class CurrentMinuteKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('minute', local)

    def get_value(self, context):
        return str(self._get_time(context).minute).ljust(2, '0')


class CurrentWeekKeyword(DateTimeKeyword):
    def __init__(self, local: bool):
        super().__init__('week', local)

    def get_value(self, context):
        return str(self._get_time(context).strftime('%V'))


class CurrentTimestampKeyword(DateTimeKeyword):
    def __init__(self):
        super().__init__('timestamp', False)

    def get_value(self, context):
        return str(int(self._get_time(context).timestamp()))


#################
# Site metadata #
#################


class SiteNameKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('site_name')

    def get_value(self, context):
        return context.project_name


class ServerNameKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('server_name')

    def get_value(self, context):
        raise ValueError(self.name + ' not implemented')  # TODO


class CurrentVersionKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('current_version')

    def get_value(self, context):
        from .. import settings
        return settings.VERSION


class SiteLanguageKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('site_lang')

    def get_value(self, context):
        return context.default_language.code


#########
# Pages #
#########


class WritingDirectionMarkKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('dir_mark')

    def get_value(self, context):
        return '&lrm;' if context.page.content_language.writing_direction == 'ltr' else '&rlm;'


class PageIdKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('page_id')

    def get_value(self, context):
        raise ValueError(self.name + ' not implemented')  # TODO


class PageLanguageKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('page_language')

    def get_value(self, context):
        return context.page.content_language.code


#############
# Revisions #
#############


class RevisionKeyword(MagicKeyword, abc.ABC):
    def __init__(self, name: str, attr: str, get_attr=str):
        """
        .

        :param name: Keyword’s main name.
        :param attr: Name of the attribute to fetch.
        :param get_attr: The function to apply to the revision to get the value to return.
        :type get_attr: typing.Callable[[WikiPy_app.models.PageRevision], str]
        """
        super().__init__('revision_' + name)
        self._attr = attr
        self._get_attr = get_attr

    def get_value(self, context):
        if hasattr(context, 'revision'):
            return self._get_attr(getattr(context.revision, self._attr))
        return ''


class RevisionIdKeyword(RevisionKeyword):
    def __init__(self):
        super().__init__('id', 'id')


class RevisionYearKeyword(RevisionKeyword):
    def __init__(self):
        super().__init__('year', 'date', lambda d: str(d.year))


class RevisionMonthKeyword(RevisionKeyword):
    def __init__(self, padded: bool):
        super().__init__('month' + ('_padded' if padded else ''), 'date',
                         lambda d: str(d.month).ljust(2, '0') if padded else str(d.month))


class RevisionDayKeyword(RevisionKeyword):
    def __init__(self, padded: bool):
        super().__init__('day' + ('_padded' if padded else ''), 'date',
                         lambda d: str(d.day).ljust(2, '0') if padded else str(d.day))


class RevisionTimestampKeyword(RevisionKeyword):
    def __init__(self):
        super().__init__('timestamp', 'date', lambda d: str(d.timestamp()))


class RevisionUserKeyword(RevisionKeyword):
    def __init__(self):
        super().__init__('user', 'author', lambda a: a.username)


class RevisionSizeKeyword(RevisionKeyword):
    def __init__(self):
        super().__init__('size', 'diff_size')


class NamespaceNameKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('namespace_name')

    def get_value(self, context):
        return context.page.namespace.get_name(local=True)


class NamespaceIdKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('namespace_id')

    def get_value(self, context):
        return str(context.page.namespace_id)


class FullPageTitleKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('full_page_title')

    def get_value(self, context):
        return context.page.full_title


class PageTitleKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('page_title')

    def get_value(self, context):
        return context.page.title


class UsernameKeyword(MagicKeyword):
    def __init__(self):
        super().__init__('username')

    def get_value(self, context):
        return context.user.username
