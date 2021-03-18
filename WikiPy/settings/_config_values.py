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
GROUP_BOTS = 'bots'
GROUP_RIGHTS_MANAGERS = 'rights_managers'

USER_GROUPS_IDS = (
    GROUP_ALL,
    GROUP_USERS,
    GROUP_EMAIL_CONFIRMED,
    GROUP_AUTOPATROLLED,
    GROUP_ADMINISTRATORS,
    GROUP_BOTS,
    GROUP_RIGHTS_MANAGERS,
)

##########
# Rights #
##########

RIGHT_READ_PAGES = 'read'
RIGHT_EDIT_PAGES = 'edit'

RIGHT_RENAME_PAGES = 'rename_pages'
RIGHT_DELETE_PAGES = 'delete_pages'
RIGHT_PROTECT_PAGES = 'protect_pages'
RIGHT_REVOKE = 'revoke'
RIGHT_VALIDATE_CHANGES = 'validate_changes'
RIGHT_HIDE_REVISIONS = 'hide_revisions'
RIGHT_BLOCK_USERS = 'block_users'
RIGHT_RENAME_USERS = 'rename_users'
RIGHT_EDIT_USERS_GROUPS = 'edit_users_groups'
RIGHT_EDIT_USER_PAGES = 'edit_user_pages'

NAMESPACE_RIGHTS = (
    RIGHT_READ_PAGES,
    RIGHT_EDIT_PAGES,
)

GLOBAL_RIGHTS = (
    RIGHT_RENAME_PAGES,
    RIGHT_DELETE_PAGES,
    RIGHT_PROTECT_PAGES,
    RIGHT_REVOKE,
    RIGHT_VALIDATE_CHANGES,
    RIGHT_HIDE_REVISIONS,
    RIGHT_BLOCK_USERS,
    RIGHT_RENAME_USERS,
    RIGHT_EDIT_USERS_GROUPS,
    RIGHT_EDIT_USER_PAGES,
)

##############
# Page types #
##############

PAGE_TYPE_WIKI = 'wiki_page'
PAGE_TYPE_STYLESHEET = 'css'
PAGE_TYPE_JAVASCRIPT = 'javascript'
PAGE_TYPE_MODULE = 'module'

PAGE_TYPES = (
    PAGE_TYPE_WIKI,
    PAGE_TYPE_STYLESHEET,
    PAGE_TYPE_JAVASCRIPT,
    PAGE_TYPE_MODULE,
)

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
