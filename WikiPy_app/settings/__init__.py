import json
import logging as _logging
import os
import re
import typing as typ

from . import _i18n as i18n
from ._config_values import *
from ._group import UserGroup
from ._namespace import Namespace
from .. import skins as _skins

PROJECT_NAME = ''

LANGUAGE = ''

MAIN_PAGE_NAMESPACE_ID = 0
MAIN_PAGE_TITLE = ''
HIDE_TITLE_ON_MAIN_PAGE = True

CASE_SENSITIVE_TITLE = True
# noinspection PyTypeChecker
INVALID_TITLE_REGEX: typ.Pattern[typ.AnyStr] = None

NAMESPACES: typ.Dict[int, Namespace] = {}

GROUPS: typ.Dict[str, UserGroup] = {}


def init(base_dir: str):
    global PROJECT_NAME, LANGUAGE, MAIN_PAGE_NAMESPACE_ID, MAIN_PAGE_TITLE, HIDE_TITLE_ON_MAIN_PAGE, \
        CASE_SENSITIVE_TITLE, NAMESPACES, INVALID_TITLE_REGEX, GROUPS

    _logging.basicConfig(format='%(levelname)s:%(message)s', level=_logging.DEBUG)

    with open(os.path.join(base_dir, 'WikiPy_app/config.json'), mode='r', encoding='UTF-8') as _config_file:
        json_config = json.load(_config_file)
        PROJECT_NAME = str(json_config['project_name'])

        LANGUAGE = str(json_config['language'])

        MAIN_PAGE_NAMESPACE_ID = int(json_config['main_page_namespace_id'])
        MAIN_PAGE_TITLE = str(json_config['main_page_title'])
        HIDE_TITLE_ON_MAIN_PAGE = bool(json_config['hide_title_on_main_page'])

        CASE_SENSITIVE_TITLE = bool(json_config['case_sensitive_titles'])

        local_rights = dict(**json_config['rights'])
        # additional_groups = dict(**json_config['additional_groups'])  # TODO

        skin_names = list(json_config['skins'])

    NAMESPACES = {}
    with open(os.path.join(base_dir, 'WikiPy_app/namespaces.json'), mode='r', encoding='UTF-8') as _namespaces_file:
        json_obj = json.load(_namespaces_file).items()

        for ns_id, ns in json_obj:
            ns_id = int(ns_id)
            ns_name = ns['name']
            ns_local_name = ns.get('local_name', None)
            ns_alias = ns.get('alias', None)

            NAMESPACES[ns_id] = Namespace(ns_id, ns_name, local_name=ns_local_name, alias=ns_alias)

    INVALID_TITLE_REGEX = re.compile(
        r'[<>_#|{}[]\x00-\x1f\x7f]|%[0-9A-Fa-f]{2}|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;')

    #################
    # Rights/Groups #
    #################

    edit_rights = {
        GROUP_ALL: {
            'namespaces': {ns_id: {k: True for k in NAMESPACE_RIGHTS}
                           for ns_id in NAMESPACES if ns_id not in [-1, 4, 16]},
            'global': {
                RIGHT_RENAME_PAGES: True,
            },
            'needs_validation': True,
            'hide_from_RC': False,
        },
        GROUP_USERS: {
            'inherits': GROUP_ALL,
        },
        GROUP_EMAIL_CONFIRMED: {
            'inherits': GROUP_USERS,
        },
        GROUP_AUTOPATROLLED: {
            'inherits': GROUP_EMAIL_CONFIRMED,
            'needs_validation': False,
        },
        GROUP_PATROLLERS: {
            'inherits': GROUP_AUTOPATROLLED,
            'global': {
                RIGHT_REVOKE: True,
                RIGHT_VALIDATE_CHANGES: True,
            },
        },
        GROUP_ADMINISTRATORS: {
            'inherits': GROUP_PATROLLERS,
            'namespaces': {
                4: {k: True for k in NAMESPACE_RIGHTS},
                16: {k: True for k in NAMESPACE_RIGHTS},
            },
            'global': {
                RIGHT_DELETE_PAGES: True,
                RIGHT_PROTECT_PAGES: True,
                RIGHT_HIDE_REVISIONS: True,
                RIGHT_BLOCK_USERS: True,
                RIGHT_RENAME_USERS: True,
            },
        },
        GROUP_BOTS: {
            'inherits': GROUP_AUTOPATROLLED,
            'hide_from_RC': True,
        },
        GROUP_BUREAUCRATS: {
            'inherits': GROUP_AUTOPATROLLED,
            'global': {RIGHT_EDIT_USERS_GROUPS: True},
        },
    }

    def _get_global_rights(group_rights, inherited_rights, local_global_rights):
        r = []

        for right in GLOBAL_RIGHTS:
            has_right = group_rights.get(right, False)
            inherits = right in inherited_rights
            if local_global_rights.get(right, has_right or inherits):
                r.append(right)

        return r

    def _get_namespace_rights(group_rights, inherited_rights, local_namespace_rights):
        r = {}

        for ns_id_ in NAMESPACES:
            r[ns_id_] = []
            if ns_id_ != -1:
                ns_rights = group_rights.get(ns_id_, {})
                for right in NAMESPACE_RIGHTS:
                    has_right = ns_rights.get(right, False)
                    inherits = right in inherited_rights.get(ns_id_, [])
                    if local_namespace_rights.get(str(ns_id_), {}).get(right, has_right or inherits):
                        r[ns_id_].append(right)

        return r

    GROUPS = {}

    for group_name, rights in edit_rights.items():
        inherited_group_name = rights.get('inherits', None)
        if inherited_group_name:
            inherited_group = GROUPS[inherited_group_name]
        else:
            inherited_group = UserGroup('', '', False, True, [], {})
        hide_rc = rights.get('hide_from_RC', inherited_group.hide_from_recent_changes)
        needs_validation = rights.get('needs_validation', inherited_group.needs_validation)
        local_group_rights = local_rights.get(group_name, {})
        namespace_rights = _get_namespace_rights(rights.get('namespaces', {}), inherited_group.namespace_edit_rights,
                                                 local_group_rights.get('namespaces', {}))
        global_rights = _get_global_rights(rights.get('global', {}), inherited_group.global_rights,
                                           local_group_rights.get('global', {}))

        GROUPS[group_name] = UserGroup(group_name, i18n.trans(f'group.{group_name}.name'), hide_rc,
                                       needs_validation, global_rights, namespace_rights)

    #########
    # Skins #
    #########

    for _skin_name in skin_names:
        _skins.load_skin(_skin_name)
