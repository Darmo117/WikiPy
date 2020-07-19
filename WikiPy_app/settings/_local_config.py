from ._config_values import *

PROJECT_NAME = 'TestWiki'  # Set project name here

LANGUAGE = 'en'  # Set project language here

MAIN_PAGE_NAMESPACE_ID = -2
MAIN_PAGE_TITLE = 'Main Page'
HIDE_TITLE_ON_MAIN_PAGE = True

FIRST_LETTER_CASE_SENSITIVE = True

##########
# Rights #
##########

ACCOUNT_REQUIRED = False

EDIT_RIGHTS = {
    GROUP_ALL: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGES],
            1: [RIGHT_EDIT_PAGES],
            2: [RIGHT_EDIT_PAGES],
            3: [RIGHT_EDIT_PAGES],
            8: [RIGHT_EDIT_PAGES],
            9: [RIGHT_EDIT_PAGES],
            10: [RIGHT_EDIT_PAGES],
            11: [RIGHT_EDIT_PAGES],
            12: [RIGHT_EDIT_PAGES],
            13: [RIGHT_EDIT_PAGES],
        },
        'other': [],
    },
    GROUP_USERS: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGES],
            1: [RIGHT_EDIT_PAGES],
            2: [RIGHT_EDIT_PAGES],
            3: [RIGHT_EDIT_PAGES],
            6: [RIGHT_EDIT_PAGES],
            7: [RIGHT_EDIT_PAGES],
            8: [RIGHT_EDIT_PAGES],
            9: [RIGHT_EDIT_PAGES],
            10: [RIGHT_EDIT_PAGES],
            11: [RIGHT_EDIT_PAGES],
            12: [RIGHT_EDIT_PAGES],
            13: [RIGHT_EDIT_PAGES],
            14: [RIGHT_EDIT_PAGES],
            15: [RIGHT_EDIT_PAGES],
        },
        'other': [],
    },
    GROUP_EMAIL_CONFIRMED: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGES],
            1: [RIGHT_EDIT_PAGES],
            2: [RIGHT_EDIT_PAGES],
            3: [RIGHT_EDIT_PAGES],
            6: [RIGHT_EDIT_PAGES],
            7: [RIGHT_EDIT_PAGES],
            8: [RIGHT_EDIT_PAGES],
            9: [RIGHT_EDIT_PAGES],
            10: [RIGHT_EDIT_PAGES],
            11: [RIGHT_EDIT_PAGES],
            12: [RIGHT_EDIT_PAGES],
            13: [RIGHT_EDIT_PAGES],
            14: [RIGHT_EDIT_PAGES],
            15: [RIGHT_EDIT_PAGES],
        },
        'other': [],
    },
    GROUP_AUTOCONFIRMED: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGES],
            1: [RIGHT_EDIT_PAGES],
            2: [RIGHT_EDIT_PAGES],
            3: [RIGHT_EDIT_PAGES],
            6: [RIGHT_EDIT_PAGES],
            7: [RIGHT_EDIT_PAGES],
            8: [RIGHT_EDIT_PAGES],
            9: [RIGHT_EDIT_PAGES],
            10: [RIGHT_EDIT_PAGES],
            11: [RIGHT_EDIT_PAGES],
            12: [RIGHT_EDIT_PAGES],
            13: [RIGHT_EDIT_PAGES],
            14: [RIGHT_EDIT_PAGES],
            15: [RIGHT_EDIT_PAGES],
        },
        'other': [],
    },
    GROUP_ADMINISTRATORS: {
        'namespaces': {
            0: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            1: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            2: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            3: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            4: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            5: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            6: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            7: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            8: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            9: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            10: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            11: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            12: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            13: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            14: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
            15: [RIGHT_EDIT_PAGES, RIGHT_DELETE_PAGES, RIGHT_RENAME_PAGES],
        },
        'other': [RIGHT_HIDE_REVISION, RIGHT_RENAME_USERS, RIGHT_EDIT_USERS_GROUPS, RIGHT_BLOCK_USERS,
                  RIGHT_PROTECT_PAGES],
    },
}

#########
# Skins #
#########

# Add additional skins below

SKINS = []
