import datetime as _dt
import json as _json
import logging as _logging
import os as _os
import re as _re
import sys as _sys
import typing as _typ

from . import _i18n as i18n
from ._config_values import *
from ._group import UserGroup
from ._namespace import Namespace
from .. import skins as _skins, special_pages as _sp, apps as _apps

VERSION = '0.1'

ALLOWED_HOSTS = []

PROJECT_NAME = ''

LANGUAGE_CODE = ''
WRITING_DIRECTION = ''

TIME_ZONE = ''
DATETIME_FORMATS: _typ.List[str] = []

MAIN_PAGE_NAMESPACE_ID = 0
MAIN_PAGE_TITLE = ''
HIDE_TITLE_ON_MAIN_PAGE = True

CASE_SENSITIVE_TITLE = True
# noinspection PyTypeChecker
INVALID_TITLE_REGEX: _typ.Pattern = None

MAIN_NAMESPACE_NAME: str = ''
NAMESPACES: _typ.Dict[int, Namespace] = {}

GROUPS: _typ.Dict[str, UserGroup] = {}

DIFF_SIZE_TAG_IMPORTANT = 500


def init(base_dir: str):
    global ALLOWED_HOSTS, PROJECT_NAME, LANGUAGE_CODE, MAIN_PAGE_NAMESPACE_ID, MAIN_PAGE_TITLE, \
        HIDE_TITLE_ON_MAIN_PAGE, CASE_SENSITIVE_TITLE, INVALID_TITLE_REGEX, TIME_ZONE, WRITING_DIRECTION, NAMESPACES, \
        GROUPS, DATETIME_FORMATS, MAIN_NAMESPACE_NAME

    _logging.basicConfig(format='%(levelname)s:%(message)s', level=_logging.DEBUG)

    config_path = _os.path.join(base_dir, _apps.WikiPyAppConfig.name, 'config.json')
    with open(config_path, mode='r', encoding='UTF-8') as _config_file:
        json_config = _json.load(_config_file)

        ALLOWED_HOSTS = list(map(str, json_config['hosts']))

        PROJECT_NAME = str(json_config['project_name'])

        LANGUAGE_CODE = str(json_config['language'])
        WRITING_DIRECTION = str(json_config['writing_direction'])

        TIME_ZONE = str(json_config['time_zone'])
        DATETIME_FORMATS = list(map(str, json_config['datetime_formats']))

        MAIN_PAGE_NAMESPACE_ID = int(json_config['main_page_namespace_id'])
        MAIN_PAGE_TITLE = str(json_config['main_page_title'])
        HIDE_TITLE_ON_MAIN_PAGE = bool(json_config['hide_title_on_main_page'])

        CASE_SENSITIVE_TITLE = bool(json_config['case_sensitive_titles'])

        MAIN_NAMESPACE_NAME = str(json_config['main_namespace_name'])

        local_rights = dict(json_config['rights'])
        # TODO handle custom groups definition
        # additional_groups = dict(**json_config['additional_groups'])

        skin_names = list(map(str, json_config['skins']))

    i18n.load_translations(base_dir)

    # Check datetime formats
    for dt_format in DATETIME_FORMATS:
        try:
            if '%' not in dt_format:
                raise ValueError('no % in format')
            _dt.datetime.now().strftime(dt_format)
        except ValueError:
            raise ValueError(f'invalid format string "{dt_format}"')
    if len(DATETIME_FORMATS) == 0:
        raise ValueError(f'no datetime formats defined')

    def load_ns_file(filename: str, ignore_translation: bool):
        ns_config_path = _os.path.join(base_dir, _apps.WikiPyAppConfig.name, filename + '.json')
        with open(ns_config_path, mode='r', encoding='UTF-8') as _namespaces_file:
            json_obj: _typ.Mapping[str, _typ.Mapping] = _json.load(_namespaces_file)

            for _ns_id, ns_json in json_obj.items():
                _ns_id = int(_ns_id)
                ns_name = str(ns_json['name'])
                if not ignore_translation:
                    ns_local_name = i18n.trans(f'namespace.{_ns_id}', none_if_undefined=True)
                else:
                    ns_local_name = None
                ns_alias = ns_json.get('alias')
                if ns_alias is not None:
                    ns_alias = str(ns_alias)
                is_talk = bool(ns_json.get('talk', False))

                # Check name and ID duplicates
                if _ns_id in NAMESPACES:
                    raise ValueError(f'duplicate namespace ID "{_ns_id}"')
                for ns in NAMESPACES.values():
                    if ns.matches_name(ns_name) or (ns_local_name is not None and ns.matches_name(ns_local_name)):
                        raise ValueError(f'duplicate namespace name or local name for IDs "{_ns_id}" and "{ns.id}"')

                NAMESPACES[_ns_id] = Namespace(_ns_id, ns_name, is_talk, local_name=ns_local_name, alias=ns_alias)

    NAMESPACES = {}
    load_ns_file('settings/_default_namespaces', ignore_translation=False)
    load_ns_file('additional_namespaces', ignore_translation=True)

    INVALID_TITLE_REGEX = _re.compile(
        r'([<>_#|{}\[\]\x00-\x1f\x7f]|%[0-9A-Fa-f]{2}|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')

    #################
    # Rights/Groups #
    #################

    rights_all = {}
    for ns_id in NAMESPACES:
        ns_rights = {k: True for k in NAMESPACE_RIGHTS}
        if ns_id in [-1, 4, 6, 16]:
            ns_rights[RIGHT_EDIT_PAGES] = False
        rights_all[ns_id] = ns_rights

    edit_rights = {
        GROUP_ALL: {
            'editable': False,
            'namespaces': rights_all,
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
            'editable': True,
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
                RIGHT_EDIT_USER_PAGES: True,
            },
        },
        GROUP_BOTS: {
            'inherits': GROUP_AUTOPATROLLED,
            'hide_from_RC': True,
        },
        GROUP_RIGHTS_MANAGERS: {
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
            group_ns_rights = group_rights.get(ns_id_, {})
            for right in NAMESPACE_RIGHTS:
                has_right = group_ns_rights.get(right, False) and (ns_id_ != -1 or right == RIGHT_READ_PAGES)
                inherits = right in inherited_rights.get(ns_id_, [])
                if local_namespace_rights.get(str(ns_id_), {}).get(right, has_right or inherits):
                    r[ns_id_].append(right)

        return r

    GROUPS = {}
    for group_name, rights in edit_rights.items():
        inherited_group_name: _typ.Optional[str] = rights.get('inherits', None)
        if inherited_group_name:
            inherited_group = GROUPS[inherited_group_name]
        else:
            inherited_group = UserGroup('', '', False, True, [], {}, False)
        editable = rights.get('editable', inherited_group.editable)
        hide_rc = rights.get('hide_from_RC', inherited_group.hide_from_recent_changes)
        needs_validation = rights.get('needs_validation', inherited_group.needs_validation)
        local_group_rights = local_rights.get(group_name, {})
        namespace_rights = _get_namespace_rights(rights.get('namespaces', {}), inherited_group.namespace_edit_rights,
                                                 local_group_rights.get('namespaces', {}))
        global_rights = _get_global_rights(rights.get('global', {}), inherited_group.global_rights,
                                           local_group_rights.get('global', {}))

        GROUPS[group_name] = UserGroup(group_name, i18n.trans(f'group.{group_name}'), hide_rc,
                                       needs_validation, global_rights, namespace_rights, editable)

    self = _sys.modules[__name__]

    _sp.load_special_pages(base_dir, self)

    for _skin_name in skin_names:
        _skins.load_skin(_skin_name, self)
