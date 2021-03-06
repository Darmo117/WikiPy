import json as _json
import logging as _logging
import os as _os
import re as _re
import typing as _typ

from . import _i18n as i18n
from . import _resource_loader as resource_loader
from ._config_values import *
from ._group import UserGroup
from ._namespace import Namespace
from .. import apps as _apps, media_backends as _media_backends, parser as _parser

VERSION = '1.0'

ALLOWED_HOSTS = []

APP_NAME = ''

BASE_DIR = ''
WIKI_APP_DIR = ''

FROM_EMAIL = ''
EMAIL_HOST = ''
EMAIL_PORT = 0
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_SSL_KEYFILE: _typ.Optional[str] = None
EMAIL_SSL_CERTFILE: _typ.Optional[str] = None
EMAIL_TIMEOUT: _typ.Optional[int] = None

PROJECT_NAME = ''

DEFAULT_LANGUAGE_CODE = ''

TIME_ZONE = ''

MAIN_PAGE_NAMESPACE_ID = 0
MAIN_PAGE_TITLE = ''
HIDE_TITLE_ON_MAIN_PAGE = True

CASE_SENSITIVE_TITLE = True
# noinspection PyTypeChecker
INVALID_TITLE_REGEX: _typ.Pattern = None

NAMESPACES: _typ.Dict[int, Namespace] = {}

GROUPS: _typ.Dict[str, UserGroup] = {}

SPECIAL_PAGES_LOCAL_NAMES: _typ.Dict[str, str] = {}

DIFF_SIZE_TAG_IMPORTANT = 500

MEDIA_BACKEND_ID = ''

WIKI_NS: Namespace
WIKI_TALK_NS: Namespace
SPECIAL_NS: Namespace
MAIN_NS: Namespace
MAIN_TALK_NS: Namespace
CATEGORY_NS: Namespace
CATEGORY_TALK_NS: Namespace
WIKIPY_NS: Namespace
WIKIPY_TALK_NS: Namespace
USER_NS: Namespace
USER_TALK_NS: Namespace
TEMPLATE_NS: Namespace
TEMPLATE_TALK_NS: Namespace
MODULE_NS: Namespace
MODULE_TALK_NS: Namespace
HELP_NS: Namespace
HELP_TALK_NS: Namespace
FILE_NS: Namespace
FILE_TALK_NS: Namespace
GADGET_NS: Namespace
GADGET_TALK_NS: Namespace

_skin_names = []
_extension_names = []


def init(base_dir: str):
    global ALLOWED_HOSTS, APP_NAME, PROJECT_NAME, DEFAULT_LANGUAGE_CODE, MAIN_PAGE_NAMESPACE_ID, MAIN_PAGE_TITLE, \
        HIDE_TITLE_ON_MAIN_PAGE, CASE_SENSITIVE_TITLE, INVALID_TITLE_REGEX, TIME_ZONE, NAMESPACES, \
        GROUPS, FROM_EMAIL, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, \
        EMAIL_USE_SSL, EMAIL_TIMEOUT, EMAIL_SSL_KEYFILE, EMAIL_SSL_CERTFILE, SPECIAL_PAGES_LOCAL_NAMES, \
        MEDIA_BACKEND_ID, WIKI_NS, WIKI_TALK_NS, SPECIAL_NS, MAIN_NS, MAIN_TALK_NS, \
        CATEGORY_NS, CATEGORY_TALK_NS, WIKIPY_NS, WIKIPY_TALK_NS, USER_NS, USER_TALK_NS, TEMPLATE_NS, \
        TEMPLATE_TALK_NS, MODULE_NS, MODULE_TALK_NS, HELP_NS, HELP_TALK_NS, FILE_NS, FILE_TALK_NS, GADGET_NS, \
        GADGET_TALK_NS, _skin_names, _extension_names, BASE_DIR, WIKI_APP_DIR

    _logging.basicConfig(format=_apps.WikiPyAppConfig.name + ':%(levelname)s:%(message)s', level=_logging.DEBUG)

    BASE_DIR = base_dir
    WIKI_APP_DIR = _os.path.join(base_dir, _apps.WikiPyAppConfig.name)

    config_path = _os.path.join(WIKI_APP_DIR, 'config.json')
    with open(config_path, mode='r', encoding='UTF-8') as _config_file:
        json_config = _json.load(_config_file)

        ALLOWED_HOSTS = list(map(str, json_config['hosts']))

        APP_NAME = str(json_config['app_name'])

        mail_obj = json_config.get('email_server')
        if mail_obj:
            FROM_EMAIL = str(mail_obj.get('from', ''))
            EMAIL_HOST = str(mail_obj.get('host', ''))
            if EMAIL_HOST:
                EMAIL_PORT = int(mail_obj['port'])
                EMAIL_HOST_USER = str(mail_obj['user'])
                EMAIL_HOST_PASSWORD = str(mail_obj['password'])
                EMAIL_USE_TLS = bool(mail_obj['use_tls'])
                EMAIL_USE_SSL = bool(mail_obj['use_ssl'])
                if EMAIL_USE_TLS or EMAIL_USE_SSL:
                    EMAIL_SSL_KEYFILE = str(mail_obj.get('ssl_keyfile'))
                    EMAIL_SSL_CERTFILE = str(mail_obj.get('ssl_certfile'))
                EMAIL_TIMEOUT = mail_obj.get('timeout')

        PROJECT_NAME = str(json_config['project_name'])

        DEFAULT_LANGUAGE_CODE = str(json_config['default_language'])

        TIME_ZONE = str(json_config['time_zone'])

        MAIN_PAGE_NAMESPACE_ID = int(json_config['main_page_namespace_id'])
        MAIN_PAGE_TITLE = str(json_config['main_page_title'])
        HIDE_TITLE_ON_MAIN_PAGE = bool(json_config['hide_title_on_main_page'])

        CASE_SENSITIVE_TITLE = bool(json_config['case_sensitive_titles'])

        MEDIA_BACKEND_ID = str(json_config['media_backend'])

        local_rights = dict(json_config['rights'])
        # TODO handle custom groups definition
        # additional_groups = dict(**json_config['additional_groups'])

        _skin_names = list(map(str, json_config['skins']))

    _extension_names = filter(
        lambda d: _os.path.isdir(_os.path.join(WIKI_APP_DIR, 'extensions', d)) and not d.startswith('_'),
        _os.listdir(_os.path.join(WIKI_APP_DIR, 'extensions'))
    )

    i18n.load_languages(base_dir)

    def load_ns_file(filename: str):
        ns_config_path = _os.path.join(WIKI_APP_DIR, filename + '.json')
        with open(ns_config_path, mode='r', encoding='UTF-8') as _namespaces_file:
            json_obj: _typ.Mapping[str, _typ.Mapping] = _json.load(_namespaces_file)

            for _ns_id, ns_json in json_obj.items():
                _ns_id = int(_ns_id)
                ns_name = str(ns_json['name'])
                ns_alias = ns_json.get('alias')
                if ns_alias is not None:
                    ns_alias = str(ns_alias)
                is_content = bool(ns_json.get('is_content', False))

                talk_ns = ns_json['talk']
                talk_ns_id = _ns_id + 1
                talk_ns_name = str(talk_ns['name'])
                talk_ns_alias = talk_ns.get('alias')
                if talk_ns_alias is not None:
                    talk_ns_alias = str(talk_ns_alias)

                # Check name and ID duplicates
                if _ns_id in NAMESPACES:
                    raise ValueError(f'duplicate namespace ID "{_ns_id}"')
                for ns in NAMESPACES.values():
                    if ns.matches_name(ns_name) or ns_alias and ns.matches_name(ns_alias):
                        raise ValueError(f'duplicate namespace name for IDs "{_ns_id}" and "{ns.id}"')
                if talk_ns_id in NAMESPACES:
                    raise ValueError(f'duplicate namespace ID "{talk_ns_id}"')
                for ns in NAMESPACES.values():
                    if ns.matches_name(talk_ns_name) or talk_ns_alias and ns.matches_name(talk_ns_alias):
                        raise ValueError(f'duplicate namespace name for IDs "{talk_ns_id}" and "{ns.id}"')

                NAMESPACES[_ns_id] = Namespace(_ns_id, ns_name, is_talk=False, can_be_main=True, is_content=is_content,
                                               alias=ns_alias)
                NAMESPACES[talk_ns_id] = Namespace(talk_ns_id, talk_ns_name, is_talk=True, is_content=False,
                                                   can_be_main=False, alias=talk_ns_alias)

    NAMESPACES = {}
    with open(_os.path.join(WIKI_APP_DIR, 'namespaces_names.json'), mode='r',
              encoding='UTF-8') as f:
        ns_names = _json.load(f)

    def get_ns_name(ident: int) -> str:
        return ns_names.get(str(ident), {}).get('name')

    def get_ns_alias(ident: int) -> str:
        return ns_names.get(str(ident), {}).get('alias')

    def get_ns_feminine_name(ident: int):
        return ns_names.get(str(ident), {}).get('feminine_name')

    def get_ns_masculine_name(ident: int):
        return ns_names.get(str(ident), {}).get('masculine_name')

    WIKI_NS = Namespace(
        -3, 'WikiNamespace',
        is_talk=False,
        is_content=False,
        can_be_main=True,
        name=get_ns_name(-3),
        alias=get_ns_alias(-3)
    )
    NAMESPACES[WIKI_NS.id] = WIKI_NS
    WIKI_TALK_NS = Namespace(
        -2, 'WikiNamespace Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(-2),
        alias=get_ns_alias(-2)
    )
    NAMESPACES[WIKI_TALK_NS.id] = WIKI_TALK_NS
    SPECIAL_NS = Namespace(
        -1, 'Special',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(-1),
        alias=get_ns_alias(-1)
    )
    NAMESPACES[SPECIAL_NS.id] = SPECIAL_NS
    MAIN_NS = Namespace(
        0, '',
        is_talk=False,
        is_content=True,
        can_be_main=True,
        name=get_ns_name(0),
        alias=get_ns_alias(0)
    )
    NAMESPACES[MAIN_NS.id] = MAIN_NS
    MAIN_TALK_NS = Namespace(
        1,
        'Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(1),
        alias=get_ns_alias(1)
    )
    NAMESPACES[MAIN_TALK_NS.id] = MAIN_TALK_NS
    CATEGORY_NS = Namespace(
        2,
        'Category',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(2),
        alias=get_ns_alias(2)
    )
    NAMESPACES[CATEGORY_NS.id] = CATEGORY_NS
    CATEGORY_TALK_NS = Namespace(
        3,
        'Category Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(3),
        alias=get_ns_alias(3)
    )
    NAMESPACES[CATEGORY_TALK_NS.id] = CATEGORY_TALK_NS
    WIKIPY_NS = Namespace(
        4,
        'WikiPy',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(4),
        alias=get_ns_alias(4)
    )
    NAMESPACES[WIKIPY_NS.id] = WIKIPY_NS
    WIKIPY_TALK_NS = Namespace(
        5,
        'WikiPy Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(5),
        alias=get_ns_alias(5)
    )
    NAMESPACES[WIKIPY_TALK_NS.id] = WIKIPY_TALK_NS
    USER_NS = Namespace(
        6,
        'User',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(6),
        alias=get_ns_alias(6),
        feminine_name=get_ns_feminine_name(6),
        masculine_name=get_ns_masculine_name(6)
    )
    NAMESPACES[USER_NS.id] = USER_NS
    USER_TALK_NS = Namespace(
        7,
        'User Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(7),
        alias=get_ns_alias(7),
        feminine_name=get_ns_feminine_name(7),
        masculine_name=get_ns_masculine_name(7)
    )
    NAMESPACES[USER_TALK_NS.id] = USER_TALK_NS
    TEMPLATE_NS = Namespace(
        8,
        'Template',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(8),
        alias=get_ns_alias(8)
    )
    NAMESPACES[TEMPLATE_NS.id] = TEMPLATE_NS
    TEMPLATE_TALK_NS = Namespace(
        9,
        'Template Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(9),
        alias=get_ns_alias(9)
    )
    NAMESPACES[TEMPLATE_TALK_NS.id] = TEMPLATE_TALK_NS
    MODULE_NS = Namespace(
        10,
        'Module',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(10),
        alias=get_ns_alias(10)
    )
    NAMESPACES[MODULE_NS.id] = MODULE_NS
    MODULE_TALK_NS = Namespace(
        11,
        'Module Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(11),
        alias=get_ns_alias(11)
    )
    NAMESPACES[MODULE_TALK_NS.id] = MODULE_TALK_NS
    HELP_NS = Namespace(
        12,
        'Help',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(12),
        alias=get_ns_alias(12)
    )
    NAMESPACES[HELP_NS.id] = HELP_NS
    HELP_TALK_NS = Namespace(
        13,
        'Help Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(13),
        alias=get_ns_alias(13)
    )
    NAMESPACES[HELP_TALK_NS.id] = HELP_TALK_NS
    FILE_NS = Namespace(
        14,
        'File',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(14),
        alias=get_ns_alias(14)
    )
    NAMESPACES[FILE_NS.id] = FILE_NS
    FILE_TALK_NS = Namespace(
        15,
        'File Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(15),
        alias=get_ns_alias(15)
    )
    NAMESPACES[FILE_TALK_NS.id] = FILE_TALK_NS
    GADGET_NS = Namespace(
        16,
        'Gadget',
        is_talk=False,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(16),
        alias=get_ns_alias(16)
    )
    NAMESPACES[GADGET_NS.id] = GADGET_NS
    GADGET_TALK_NS = Namespace(
        17,
        'Gadget Talk',
        is_talk=True,
        is_content=False,
        can_be_main=False,
        name=get_ns_name(17),
        alias=get_ns_alias(17)
    )
    NAMESPACES[GADGET_TALK_NS.id] = GADGET_TALK_NS

    load_ns_file('additional_namespaces')

    if not NAMESPACES[MAIN_PAGE_NAMESPACE_ID].can_be_main:
        raise ValueError(f'invalid main page namespace ID')

    with open(_os.path.join(WIKI_APP_DIR, 'special_pages_names.json'), mode='r',
              encoding='UTF-8') as f:
        for k, v in _json.load(f).items():
            SPECIAL_PAGES_LOCAL_NAMES[k] = str(v)

    INVALID_TITLE_REGEX = _re.compile(
        r'([@<>_#|{}\[\]\x00-\x1f\x7f]|%[0-9A-Fa-f]{2}|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')

    #################
    # Rights/Groups #
    #################

    rights_all = {}
    for ns_id in NAMESPACES:
        ns_rights = {k: True for k in NAMESPACE_RIGHTS}
        if ns_id in [SPECIAL_NS.id, WIKIPY_NS.id, USER_NS.id, GADGET_NS.id]:
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
                WIKIPY_NS.id: {k: True for k in NAMESPACE_RIGHTS},
                GADGET_NS.id: {k: True for k in NAMESPACE_RIGHTS},
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
                has_right = group_ns_rights.get(right, False) and (ns_id_ != SPECIAL_NS.id or right == RIGHT_READ_PAGES)
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
            inherited_group = UserGroup('', False, True, [], {}, False)
        editable = rights.get('editable', inherited_group.editable)
        hide_rc = rights.get('hide_from_RC', inherited_group.hide_from_recent_changes)
        needs_validation = rights.get('needs_validation', inherited_group.needs_validation)
        local_group_rights = local_rights.get(group_name, {})
        namespace_rights = _get_namespace_rights(rights.get('namespaces', {}), inherited_group.namespace_edit_rights,
                                                 local_group_rights.get('namespaces', {}))
        global_rights = _get_global_rights(rights.get('global', {}), inherited_group.global_rights,
                                           local_group_rights.get('global', {}))

        GROUPS[group_name] = UserGroup(group_name, hide_rc, needs_validation, global_rights, namespace_rights, editable)

    _media_backends.register_default()
    if not _media_backends.get_backend(MEDIA_BACKEND_ID):
        raise ValueError(f'invalid media backend ID "{MEDIA_BACKEND_ID}"')


def post_load():
    # Avoid circular imports
    from .. import special_pages, api, skins, extensions

    _logging.info('Loading skins???')
    ok = 0
    for skin_name in _skin_names:
        ok += skins.load_skin(skin_name)
    if ok == 0:
        raise RuntimeError('No skins loaded, abort.')
    _logging.info(f'Skins loaded (errors: {len(_skin_names) - ok}).')

    _logging.info('Loading extensions???')
    ok = 0
    for extension_name in _extension_names:
        _logging.info(f'Loading extension "{extension_name}"???')
        ok += extensions.load_extension(extension_name)
        ext = extensions.get_extension(extension_name)
        ext.load_magic_keywords()
        ext.load_parser_functions()
        _logging.info(f'Extension loaded successfully.')
    _logging.info(f'Extensions loaded (errors: {len(_skin_names) - ok}).')

    _parser.load_magic_keywords()
    _parser.load_functions()
    special_pages.load_special_pages()
    api.open_email_connection()
