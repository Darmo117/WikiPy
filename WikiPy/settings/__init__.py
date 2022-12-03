"""
This module defines all settings for the wiki.
"""
import json as _json
import logging as _logging
import os as _os
import pathlib as _pathlib
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

# noinspection PyTypeChecker
BASE_DIR: _pathlib.Path = None
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
SPECIAL_NS: Namespace
MAIN_NS: Namespace
CATEGORY_NS: Namespace
WIKIPY_NS: Namespace
USER_NS: Namespace
TEMPLATE_NS: Namespace
MODULE_NS: Namespace
HELP_NS: Namespace
FILE_NS: Namespace
GADGET_NS: Namespace

_skin_names = []
_extension_names = []


def init(base_dir: _pathlib.Path):
    """
    Initializes the settings. Should be called within the project’s settings.

    :param base_dir: The project’s root directory.
    """
    global ALLOWED_HOSTS, APP_NAME, PROJECT_NAME, DEFAULT_LANGUAGE_CODE, MAIN_PAGE_NAMESPACE_ID, MAIN_PAGE_TITLE, \
        HIDE_TITLE_ON_MAIN_PAGE, CASE_SENSITIVE_TITLE, INVALID_TITLE_REGEX, TIME_ZONE, NAMESPACES, \
        GROUPS, FROM_EMAIL, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS, \
        EMAIL_USE_SSL, EMAIL_TIMEOUT, EMAIL_SSL_KEYFILE, EMAIL_SSL_CERTFILE, SPECIAL_PAGES_LOCAL_NAMES, \
        MEDIA_BACKEND_ID, WIKI_NS, SPECIAL_NS, MAIN_NS, CATEGORY_NS, WIKIPY_NS, USER_NS, TEMPLATE_NS, MODULE_NS, \
        HELP_NS, FILE_NS, GADGET_NS, _skin_names, _extension_names, BASE_DIR, WIKI_APP_DIR

    _logging.basicConfig(format=_apps.WikiPyConfig.name + ':%(levelname)s:%(message)s', level=_logging.DEBUG)

    BASE_DIR = base_dir
    WIKI_APP_DIR = _os.path.join(base_dir, _apps.WikiPyConfig.name)

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

    _extension_names = list(filter(
        lambda d: _os.path.isdir(_os.path.join(WIKI_APP_DIR, 'extensions', d)) and not d.startswith('_'),
        _os.listdir(_os.path.join(WIKI_APP_DIR, 'extensions'))
    ))

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
                allows_subpages = bool(ns_json.get('allows_subpages', True))
                has_talks = bool(ns_json.get('has_talks', True))

                # Check name and ID duplicates
                if _ns_id in NAMESPACES:
                    raise ValueError(f'duplicate namespace ID "{_ns_id}"')
                for ns in NAMESPACES.values():
                    if ns.matches_name(ns_name) or ns_alias and ns.matches_name(ns_alias):
                        raise ValueError(f'duplicate namespace name for IDs "{_ns_id}" and "{ns.id}"')

                NAMESPACES[_ns_id] = Namespace(_ns_id, ns_name, has_talks=has_talks, can_be_main=True,
                                               is_content=is_content, allows_subpages=allows_subpages, alias=ns_alias)

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

    id_ = -2
    WIKI_NS = Namespace(
        id_, 'WikiNamespace',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=True,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = WIKI_NS
    id_ = -1
    SPECIAL_NS = Namespace(
        id_, 'Special',
        has_talks=False,
        is_content=False,
        allows_subpages=False,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = SPECIAL_NS
    id_ = 0
    MAIN_NS = Namespace(
        id_, '',
        has_talks=True,
        is_content=True,
        allows_subpages=bool(json_config.get('main_namespace_allows_subpages', False)),
        can_be_main=True,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = MAIN_NS
    id_ = 1
    CATEGORY_NS = Namespace(
        id_, 'Category',
        has_talks=True,
        is_content=False,
        allows_subpages=False,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = CATEGORY_NS
    id_ = 2
    WIKIPY_NS = Namespace(
        id_, 'WikiPy',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = WIKIPY_NS
    id_ = 3
    USER_NS = Namespace(
        id_, 'User',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_),
        feminine_name=get_ns_feminine_name(id_),
        masculine_name=get_ns_masculine_name(id_),
        requires_rights=(RIGHT_EDIT_SITE_INTERFACE,)
    )
    NAMESPACES[id_] = USER_NS
    id_ = 4
    TEMPLATE_NS = Namespace(
        id_, 'Template',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = TEMPLATE_NS
    id_ = 5
    MODULE_NS = Namespace(
        id_, 'Module',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = MODULE_NS
    id_ = 6
    HELP_NS = Namespace(
        id_, 'Help',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = HELP_NS
    id_ = 7
    FILE_NS = Namespace(
        id_, 'File',
        has_talks=True,
        is_content=False,
        allows_subpages=False,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_)
    )
    NAMESPACES[id_] = FILE_NS
    id_ = 8
    GADGET_NS = Namespace(
        id_, 'Gadget',
        has_talks=True,
        is_content=False,
        allows_subpages=True,
        can_be_main=False,
        name=get_ns_name(id_),
        alias=get_ns_alias(id_),
        requires_rights=(RIGHT_EDIT_GADGETS,)
    )
    NAMESPACES[id_] = GADGET_NS

    load_ns_file('additional_namespaces')

    if not NAMESPACES[MAIN_PAGE_NAMESPACE_ID].can_be_main:
        raise ValueError(f'invalid main page namespace ID "{MAIN_PAGE_NAMESPACE_ID}"')

    with open(_os.path.join(WIKI_APP_DIR, 'special_pages_names.json'), mode='r',
              encoding='UTF-8') as f:
        for k, v in _json.load(f).items():
            SPECIAL_PAGES_LOCAL_NAMES[k] = str(v)

    INVALID_TITLE_REGEX = _re.compile(
        r'([@<>_#|{}\[\]\x00-\x1f\x7f]|%[0-9A-Fa-f]{2}|&[A-Za-z0-9\x80-\xff]+;|&#[0-9]+;|&#x[0-9A-Fa-f]+;)')

    #################
    # Rights/Groups #
    #################

    group_all = UserGroup(
        GROUP_ALL,
        rights=[
            RIGHT_CREATE_ACCOUNT,
            RIGHT_CREATE_PAGES,
            RIGHT_CREATE_TOPICS,
            RIGHT_EDIT_TOPICS,
            RIGHT_POST_MESSAGES,
            RIGHT_EDIT_OWN_MESSAGES,
            RIGHT_READ_PAGES,
            RIGHT_EDIT_PAGES,
        ],
        editable=False
    )
    group_users = UserGroup(
        GROUP_USERS,
        rights=[
            RIGHT_EDIT_MY_PREFERENCES,
            RIGHT_EDIT_MY_WATCHLIST,
            RIGHT_WRITE_API,
            RIGHT_IP_BLOCK_EXEMPT,
            RIGHT_SEND_EMAILS,
            RIGHT_EDIT_MY_INTERFACE,
            RIGHT_PURGE_CACHE,
        ],
        editable=False
    )
    group_email_confirmed = UserGroup(
        GROUP_EMAIL_CONFIRMED,
        rights=[
            RIGHT_RENAME_PAGES,
        ],
        editable=False
    )
    group_autopatrolled = UserGroup(
        GROUP_AUTOPATROLLED,
        rights=[
            RIGHT_AUTOPATROLLED,
            RIGHT_PIN_TOPICS,
        ],
        editable=True
    )
    group_patrollers = UserGroup(
        GROUP_PATROLLERS,
        rights=[
            RIGHT_PATROL,
            RIGHT_ROLLBACK,
        ],
        editable=True
    )
    group_administrators = UserGroup(
        GROUP_ADMINISTRATORS,
        rights=[
            RIGHT_VIEW_DELETED_TOPICS,
            RIGHT_VIEW_DELETED_MESSAGES,
            RIGHT_PROTECT_PAGES,
            RIGHT_EDIT_USER_PAGES,
            RIGHT_RENAME_USERS,
            RIGHT_RENAME_FILES,
            RIGHT_DELETE_PAGES,
            RIGHT_RESTORE_PAGES,
            RIGHT_DELETE_REVISIONS,
            RIGHT_RESTORE_REVISIONS,
            RIGHT_VIEW_DELETED_REVISIONS,
            RIGHT_VIEW_DELETED_LOG_ENTRIES,
            RIGHT_DELETE_LOG_ENTRIES,
            RIGHT_VIEW_TITLES_BLACKLIST,
            RIGHT_EDIT_TITLES_BLACKLIST,
            RIGHT_BLOCK_USERS,
            RIGHT_EDIT_PAGE_LANGUAGE,
            RIGHT_BLOCK_EMAILS,
            RIGHT_MERGE_PAGES,
            RIGHT_EDIT_PAGE_CONTENT_MODEL,
            RIGHT_MASS_DELETE_PAGES,
        ],
        editable=True
    )
    group_message_admins = UserGroup(
        GROUP_MESSAGE_ADMINISTRATORS,
        rights=[
            RIGHT_DELETE_TOPICS,
            RIGHT_RESTORE_TOPICS,
            RIGHT_VIEW_DELETED_TOPICS,
            RIGHT_EDIT_MESSAGES,
            RIGHT_DELETE_MESSAGES,
            RIGHT_RESTORE_MESSAGES,
            RIGHT_VIEW_DELETED_MESSAGES,
        ],
        editable=True
    )
    group_interface_admins = UserGroup(
        GROUP_INTERFACE_ADMINISTRATORS,
        rights=[
            RIGHT_EDIT_SITE_INTERFACE,
            RIGHT_EDIT_GADGETS,
            RIGHT_EDIT_USER_INTERFACE,
        ],
        editable=True
    )
    group_groups_managers = UserGroup(
        GROUP_GROUPS_MANAGERS,
        rights=[
            RIGHT_EDIT_USERS_GROUPS,
        ],
        editable=True
    )
    group_user_checkers = UserGroup(
        GROUP_USER_CHECKERS,
        rights=[
            RIGHT_VIEW_USER_PRIVATE_DETAILS,
        ],
        editable=True
    )
    group_file_managers = UserGroup(
        GROUP_FILE_MANAGERS,
        rights=[
            RIGHT_RENAME_FILES,
            RIGHT_UPLOAD_FILES,
            RIGHT_REUPLOAD_FILES,
        ],
        editable=True
    )
    group_abuse_filter_modifiers = UserGroup(
        GROUP_ABUSE_FILTER_MODIFIERS,
        rights=[  # TODO abuse filter managers rights
        ],
        editable=True
    )
    group_bots = UserGroup(
        GROUP_BOTS,
        rights=[
            RIGHT_NO_RATE_LIMIT,
            RIGHT_BOT,
        ],
        editable=True
    )

    GROUPS = {
        GROUP_ALL: group_all,
        GROUP_USERS: group_users,
        GROUP_EMAIL_CONFIRMED: group_email_confirmed,
        GROUP_AUTOPATROLLED: group_autopatrolled,
        GROUP_PATROLLERS: group_patrollers,
        GROUP_ADMINISTRATORS: group_administrators,
        GROUP_INTERFACE_ADMINISTRATORS: group_interface_admins,
        GROUP_MESSAGE_ADMINISTRATORS: group_message_admins,
        GROUP_GROUPS_MANAGERS: group_groups_managers,
        GROUP_USER_CHECKERS: group_user_checkers,
        GROUP_FILE_MANAGERS: group_file_managers,
        GROUP_ABUSE_FILTER_MODIFIERS: group_abuse_filter_modifiers,
        GROUP_BOTS: group_bots,
    }

    _media_backends.register_default()
    if not _media_backends.get_backend(MEDIA_BACKEND_ID):
        raise ValueError(f'invalid media backend ID "{MEDIA_BACKEND_ID}"')


def post_load():
    """
    This function finalizes wiki loading.
    Load order:
        - built-in logs
        - skins
        - extensions
        - parser’s magic keyword and functions (including extensions)
        - special pages (including extensions)
        - email connection
    It should be called within the ready() method of the wiki’s config class.
    """
    # Avoid circular imports
    from ..api import emails as api_emails, logs as api_logs
    from .. import special_pages, skins, extensions, models

    _logging.info('Registering logs…')
    models.register_journals(api_logs)
    _logging.info('Logs registered.')

    _logging.info('Loading skins…')
    ok = 0
    for skin_name in _skin_names:
        ok += skins.load_skin(skin_name)
    if ok == 0:
        raise RuntimeError('No skins loaded, abort.')
    _logging.info(f'Skins loaded (errors: {len(_skin_names) - ok}).')

    _logging.info('Loading extensions…')
    ok = 0
    for extension_name in _extension_names:
        _logging.info(f'Loading extension "{extension_name}"…')
        loaded = extensions.load_extension(extension_name)
        if loaded:
            ext = extensions.get_extension(extension_name)
            ext.load_magic_keywords()
            ext.load_parser_functions()
            ext.register_logs(api_logs)
            ok += 1
            _logging.info(f'Extension loaded successfully.')
    _logging.info(f'Extensions loaded (errors: {len(_extension_names) - ok}).')

    _parser.load_magic_keywords()
    _parser.load_functions()
    special_pages.load_special_pages()
    api_emails.open_email_connection()
