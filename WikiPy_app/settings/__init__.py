from . import _namespaces, _local_config, _l10n as l10n
from ._config_values import *
from .. import skins as _skins
import logging as _logging

_logging.basicConfig(format='%(levelname)s:%(message)s', level=_logging.DEBUG)

PROJECT_NAME = _local_config.PROJECT_NAME

MAIN_PAGE_NAMESPACE_ID = _local_config.MAIN_PAGE_NAMESPACE_ID
MAIN_PAGE_TITLE = _local_config.MAIN_PAGE_TITLE

NAMESPACES = _namespaces.NAMESPACES

##########
# Rights #
##########

ACCOUNT_REQUIRED = _local_config.ACCOUNT_REQUIRED

EDIT_RIGHTS = {
    GROUP_ANONYMOUS: {
        'namespaces': {},
        'other': [],
    },
    GROUP_NEW_ACCOUNT: {
        'namespaces': {},
        'other': [],
    },
    GROUP_EMAIL_CONFIRMED: {
        'namespaces': {},
        'other': [],
    },
    GROUP_AUTOPATROLLED: {
        'namespaces': {},
        'other': [],
    },
    GROUP_ADMINISTRATOR: {
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
