"""This module defines global values to be used anywhere."""
import sys

WIKI_SETUP_PAGE_TITLE = 'WikiSetup'

##########
# Groups #
##########

GROUP_ALL = 'all'
GROUP_USERS = 'users'
GROUP_EMAIL_CONFIRMED = 'email_confirmed'
GROUP_AUTOPATROLLED = 'autopatrolled'
GROUP_PATROLLERS = 'patrollers'
GROUP_ADMINISTRATORS = 'administrators'
GROUP_INTERFACE_ADMINISTRATORS = 'interface_administrators'
GROUP_GROUPS_MANAGERS = 'groups_managers'
GROUP_ABUSE_FILTER_MODIFIERS = 'abuse_filter_modifiers'
GROUP_USER_CHECKERS = 'user_checkers'
GROUP_FILE_MANAGERS = 'file_managers'
GROUP_MESSAGE_ADMINISTRATORS = 'message_administrators'
GROUP_BOTS = 'bots'

USER_GROUPS_IDS = tuple(v for k, v in sys.modules[__name__].__dict__.items() if k.startswith('GROUP_'))

##########
# Rights #
##########

RIGHT_CREATE_ACCOUNT = 'create_account'

RIGHT_CREATE_PAGES = 'create_pages'
RIGHT_READ_PAGES = 'read'
RIGHT_EDIT_PAGES = 'edit'
RIGHT_RENAME_PAGES = 'rename_pages'
RIGHT_PROTECT_PAGES = 'protect_pages'
RIGHT_DELETE_PAGES = 'delete_pages'
RIGHT_RESTORE_PAGES = 'restore_pages'
RIGHT_EDIT_PAGE_LANGUAGE = 'edit_page_language'
RIGHT_EDIT_PAGE_CONTENT_MODEL = 'edit_page_content_model'
RIGHT_MERGE_PAGES = 'merge_pages'
RIGHT_MASS_DELETE_PAGES = 'mass_delete_pages'
RIGHT_PURGE_CACHE = 'purge_cache'

RIGHT_DELETE_REVISIONS = 'delete_revisions'
RIGHT_RESTORE_REVISIONS = 'restore_revisions'
RIGHT_VIEW_DELETED_REVISIONS = 'view_deleted_revisions'

RIGHT_UPLOAD_FILES = 'upload_files'
RIGHT_RENAME_FILES = 'rename_files'
RIGHT_REUPLOAD_FILES = 'reupload_files'

RIGHT_CREATE_TOPICS = 'create_topics'
RIGHT_EDIT_TOPICS = 'edit_topics'
RIGHT_PIN_TOPICS = 'pin_topics'
RIGHT_DELETE_TOPICS = 'delete_topics'
RIGHT_RESTORE_TOPICS = 'restore_topics'
RIGHT_VIEW_DELETED_TOPICS = 'view_deleted_topics'

RIGHT_POST_MESSAGES = 'post_messages'
RIGHT_EDIT_MESSAGES = 'edit_messages'
RIGHT_EDIT_OWN_MESSAGES = 'edit_own_messages'
RIGHT_DELETE_MESSAGES = 'delete_messages'
RIGHT_RESTORE_MESSAGES = 'restore_messages'
RIGHT_VIEW_DELETED_MESSAGES = 'view_deleted_messages'

RIGHT_WRITE_API = 'write_api'
RIGHT_NO_RATE_LIMIT = 'no_rate_limit'

RIGHT_AUTOPATROLLED = 'autopatrolled'
RIGHT_PATROL = 'patrol'
RIGHT_ROLLBACK = 'rollback'

RIGHT_EDIT_MY_PREFERENCES = 'edit_my_preferences'
RIGHT_EDIT_MY_WATCHLIST = 'edit_my_watchlist'
RIGHT_EDIT_USER_PAGES = 'edit_user_pages'
RIGHT_RENAME_USERS = 'rename_users'
RIGHT_EDIT_USERS_GROUPS = 'edit_users_groups'
RIGHT_VIEW_USER_PRIVATE_DETAILS = 'view_user_private_details'
RIGHT_IP_BLOCK_EXEMPT = 'ip_block_exempt'
RIGHT_BLOCK_USERS = 'block_users'
RIGHT_SEND_EMAILS = 'send_emails'
RIGHT_BLOCK_EMAILS = 'block_emails'

RIGHT_EDIT_SITE_INTERFACE = 'edit_site_interface'
RIGHT_EDIT_GADGETS = 'edit_gadgets'
RIGHT_EDIT_USER_INTERFACE = 'edit_user_interface'
RIGHT_EDIT_MY_INTERFACE = 'edit_my_interface'

RIGHT_DELETE_LOG_ENTRIES = 'delete_log_entries'
RIGHT_VIEW_DELETED_LOG_ENTRIES = 'view_deleted_log_entries'

RIGHT_VIEW_TITLES_BLACKLIST = 'view_titles_blacklist'
RIGHT_EDIT_TITLES_BLACKLIST = 'edit_titles_blacklist'

RIGHT_BOT = 'bot'

RIGHTS = tuple(v for k, v in sys.modules[__name__].__dict__.items() if k.startswith('RIGHT_'))

##############
# Page types #
##############

PAGE_TYPE_WIKI = 'wiki_page'
PAGE_TYPE_STYLESHEET = 'css'
PAGE_TYPE_JAVASCRIPT = 'javascript'
PAGE_TYPE_MODULE = 'module'

PAGE_TYPES = tuple(v for k, v in sys.modules[__name__].__dict__.items() if k.startswith('PAGE_TYPE_'))

##############
# File types #
##############

IMAGE_FORMATS = (
    'jpeg',
    'jpg',
    'png',
    'bmp',
    'gif',
    'svg',
    'tiff',
)

VIDEO_FORMATS = (
    'mp4',
    'ogg',
    'ogv',
    'webm',
)

AUDIO_FORMATS = (
    'mp3',
    'ogg',
    'oga',
    'mid',
)

MEDIA_FORMATS = tuple({
    *IMAGE_FORMATS,
    *VIDEO_FORMATS,
    *AUDIO_FORMATS,
})

IMAGE_PREVIEW_SIZES = (
    200, 300, 400, 500, 600, 700, 800,
    1000, 1200, 1500, 1800,
    2000, 2500,
    3000
)

THUMBNAIL_SIZES = (
    100, 120, 150, 180,
    200, 220, 250, 280,
    300, 320, 350, 380,
    400, 420, 450, 480,
    500, 520, 550, 580,
    600
)

REVISIONS_LIST_PAGE_MIN = 1
REVISIONS_LIST_PAGE_MAX = 1000

RC_DAYS_MIN = 1
RC_DAYS_MAX = 30
RC_REVISIONS_MIN = 1
RC_REVISIONS_MAX = 1000

MAX_REDIRECTS_DEPTH = 20
