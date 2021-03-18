import datetime
import logging
import typing as typ

from .. import models


def register_log(log_id: str, log_class: typ.Type[models.LogEntry]):
    global _LOGS
    if not issubclass(log_class, models.LogEntry):
        raise TypeError(f'invalid log class "{log_class}"')
    if log_id in _LOGS:
        raise ValueError(f'ID "{log_id}" already registered')
    log_class.registry_id = log_id
    _LOGS[log_id] = log_class
    logging.info(f'Registered log "{log_id}".')


def get_log_ids() -> typ.Sequence[str]:
    return list(_LOGS.keys())


def get_log_entries(
        log_id: str,
        performer: str = None,
        from_date: datetime.datetime = None,
        to_date: datetime.datetime = None,
        page_title_or_username: str = None
) -> typ.Sequence[models.LogEntry]:
    _ensure_log_exists(log_id)
    return _LOGS[log_id].search(performer, from_date, to_date, page_title_or_username=page_title_or_username)


def add_log_entry(log_id: str, performer: models.User = None, **kwargs):
    _ensure_log_exists(log_id)
    _LOGS[log_id](author=performer.django_user if performer else None, **kwargs).save()


def _ensure_log_exists(log_id: str):
    if log_id not in _LOGS:
        raise ValueError(f'no log with ID "{log_id}" registered')


_LOGS: typ.Dict[str, typ.Type[models.LogEntry]] = {}

__all__ = [
    'register_log',
    'get_log_ids',
    'get_log_entries',
    'add_log_entry',
]
