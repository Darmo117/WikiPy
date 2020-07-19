import logging as _logging
import re

from . import _namespaces, _local_config, _l10n as l10n
from ._config_values import *
from .. import skins as _skins

_logging.basicConfig(format='%(levelname)s:%(message)s', level=_logging.DEBUG)

PROJECT_NAME = _local_config.PROJECT_NAME

LANGUAGE = _local_config.LANGUAGE

MAIN_PAGE_NAMESPACE_ID = _local_config.MAIN_PAGE_NAMESPACE_ID
MAIN_PAGE_TITLE = _local_config.MAIN_PAGE_TITLE
HIDE_TITLE_ON_MAIN_PAGE = _local_config.HIDE_TITLE_ON_MAIN_PAGE

NAMESPACES = _namespaces.NAMESPACES

CASE_SENSITIVE_TITLE = _local_config.FIRST_LETTER_CASE_SENSITIVE

INVALID_TITLE_REGEX = re.compile(
    r'[<>_#|{}[\]\x00-\x1f\x7f]|%[0-9A-Fa-f]{2}|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;')

##########
# Rights #
##########

ACCOUNT_REQUIRED = _local_config.ACCOUNT_REQUIRED

EDIT_RIGHTS = {
    GROUP_ALL: {
        'namespaces': {},
        'other': [],
    },
    GROUP_USERS: {
        'namespaces': {},
        'other': [],
    },
    GROUP_EMAIL_CONFIRMED: {
        'namespaces': {},
        'other': [],
    },
    GROUP_AUTOCONFIRMED: {
        'namespaces': {},
        'other': [],
    },
    GROUP_ADMINISTRATORS: {
        'namespaces': {},
        'other': [],
    },
}

for _group, _rights in _local_config.EDIT_RIGHTS.items():
    for _ns_id in NAMESPACES:
        EDIT_RIGHTS[_group]['namespaces'][_ns_id] = []

    if _group in EDIT_RIGHTS:
        if 'namespaces' in _rights:
            for _ns_id, _ns_rights in _rights['namespaces'].items():
                if _ns_id in NAMESPACES:
                    for _right in _ns_rights:
                        if _right in PAGE_EDIT_RIGHTS:
                            EDIT_RIGHTS[_group]['namespaces'][_ns_id].append(_right)
                        else:
                            _logging.warning(f'invalid page edit right "{_right}", ignored')
                else:
                    _logging.warning(f'invalid namespace ID "{_ns_id}", ignored')
        if 'other' in _rights:
            for _right in _rights['other']:
                if _right in OTHER_RIGHTS:
                    EDIT_RIGHTS[_group]['other'].append(_right)
                else:
                    _logging.warning(f'invalid user right "{_right}", ignored')

#########
# Skins #
#########

_skins.load_skin('default')

for _skin in _local_config.SKINS:
    _skins.load_skin(_skin)
