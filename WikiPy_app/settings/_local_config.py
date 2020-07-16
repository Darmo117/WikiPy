from ._config_values import *

PROJECT_NAME = 'DjangoWiki'  # Set project name here

MAIN_PAGE_NAMESPACE_ID = 0
MAIN_PAGE_TITLE = 'Main Page'

##########
# Rights #
##########

ACCOUNT_REQUIRED = False

EDIT_RIGHTS = {
    GROUP_ANONYMOUS: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGE],
            1: [RIGHT_EDIT_PAGE],
            2: [RIGHT_EDIT_PAGE],
            3: [RIGHT_EDIT_PAGE],
            8: [RIGHT_EDIT_PAGE],
            9: [RIGHT_EDIT_PAGE],
            10: [RIGHT_EDIT_PAGE],
            11: [RIGHT_EDIT_PAGE],
            12: [RIGHT_EDIT_PAGE],
            13: [RIGHT_EDIT_PAGE],
        },
        'other': [],
    },
    GROUP_NEW_ACCOUNT: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGE],
            1: [RIGHT_EDIT_PAGE],
            2: [RIGHT_EDIT_PAGE],
            3: [RIGHT_EDIT_PAGE],
            6: [RIGHT_EDIT_PAGE],
            7: [RIGHT_EDIT_PAGE],
            8: [RIGHT_EDIT_PAGE],
            9: [RIGHT_EDIT_PAGE],
            10: [RIGHT_EDIT_PAGE],
            11: [RIGHT_EDIT_PAGE],
            12: [RIGHT_EDIT_PAGE],
            13: [RIGHT_EDIT_PAGE],
            14: [RIGHT_EDIT_PAGE],
            15: [RIGHT_EDIT_PAGE],
        },
        'other': [],
    },
    GROUP_EMAIL_CONFIRMED: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGE],
            1: [RIGHT_EDIT_PAGE],
            2: [RIGHT_EDIT_PAGE],
            3: [RIGHT_EDIT_PAGE],
            6: [RIGHT_EDIT_PAGE],
            7: [RIGHT_EDIT_PAGE],
            8: [RIGHT_EDIT_PAGE],
            9: [RIGHT_EDIT_PAGE],
            10: [RIGHT_EDIT_PAGE],
            11: [RIGHT_EDIT_PAGE],
            12: [RIGHT_EDIT_PAGE],
            13: [RIGHT_EDIT_PAGE],
            14: [RIGHT_EDIT_PAGE],
            15: [RIGHT_EDIT_PAGE],
        },
        'other': [],
    },
    GROUP_AUTOPATROLLED: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGE],
            1: [RIGHT_EDIT_PAGE],
            2: [RIGHT_EDIT_PAGE],
            3: [RIGHT_EDIT_PAGE],
            6: [RIGHT_EDIT_PAGE],
            7: [RIGHT_EDIT_PAGE],
            8: [RIGHT_EDIT_PAGE],
            9: [RIGHT_EDIT_PAGE],
            10: [RIGHT_EDIT_PAGE],
            11: [RIGHT_EDIT_PAGE],
            12: [RIGHT_EDIT_PAGE],
            13: [RIGHT_EDIT_PAGE],
            14: [RIGHT_EDIT_PAGE],
            15: [RIGHT_EDIT_PAGE],
        },
        'other': [],
    },
    GROUP_ADMINISTRATOR: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            1: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            2: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            3: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            4: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            5: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            6: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            7: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            8: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            9: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            10: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            11: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            12: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            13: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            14: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
            15: [RIGHT_EDIT_PAGE, RIGHT_DELETE_PAGE, RIGHT_RENAME_PAGE],
        },
        'other': [RIGHT_HIDE_REVISION, RIGHT_RENAME_USERS, RIGHT_EDIT_USERS_GROUPS, RIGHT_BAN_USERS,
                  RIGHT_PROTECT_PAGES],
    },
}

#########
# Skins #
#########

# Add additional skins below

SKINS = []
