import logging
import os
import secrets
import string

import django.contrib.auth.models as dj_models

from WikiPy import settings as wpy_settings
from . import api, settings, apps

WIKI_USER_NAME = 'WikiPy'
_COMMENT = 'Wiki setup.'

INVALID_USERNAME = 'invalid_username'
INVALID_PASSWORD = 'invalid_password'
INVALID_EMAIL = 'invalid_email'
INVALID_SECRET_KEY = 'invalid_secret_key'
SUCCESS = 'ok'


def are_pages_setup():
    return dj_models.User.objects.filter(username=WIKI_USER_NAME).count()


def generate_secret_key_file() -> bool:
    path = os.path.join(wpy_settings.BASE_DIR, apps.WikiPyAppConfig.name, 'SETUP_SECRET_KEY')
    if not os.path.exists(path):
        chars = string.ascii_letters + string.digits
        secret_key = ''.join(secrets.choice(chars) for _ in range(20))
        with open(path, mode='w', encoding='UTF-8') as f:
            f.write(secret_key)
            f.flush()
        return True
    return False


def setup(username: str, password: str, email: str, secret_key: str) -> str:
    main_page = api.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
    project_name = settings.PROJECT_NAME

    logging.info('Creating administrator…')

    try:
        with open('WikiPy_app/SETUP_SECRET_KEY', mode='r', encoding='UTF-8') as f:
            setup_secret_key = f.readline()
            if secret_key != setup_secret_key:
                return INVALID_SECRET_KEY
    except FileNotFoundError:
        raise FileNotFoundError('no secret key file defined')

    try:
        admin = api.create_user(username, password=password, email=email)
    except (api.InvalidUsernameError, api.DuplicateUsernameError):
        return INVALID_USERNAME
    except api.InvalidPasswordError:
        return INVALID_PASSWORD
    except api.InvalidEmailError:
        return INVALID_EMAIL

    api.add_user_to_group(admin, settings.GROUP_AUTOPATROLLED, auto=True)
    api.add_user_to_group(admin, settings.GROUP_PATROLLERS, auto=True)
    api.add_user_to_group(admin, settings.GROUP_ADMINISTRATORS, auto=True)
    api.add_user_to_group(admin, settings.GROUP_RIGHTS_MANAGERS, auto=True)

    logging.info('Done.')

    logging.info('Setting up default pages…')

    password = dj_models.User.objects.make_random_password(length=100)
    wikiuser = api.create_user(WIKI_USER_NAME, password=password, ignore_email=True)
    api.add_user_to_group(wikiuser, settings.GROUP_ADMINISTRATORS, auto=True)
    api.add_user_to_group(wikiuser, settings.GROUP_BOTS, auto=True)

    api.submit_page_content(4, 'Message-BadTitle', wikiuser,
                            'The requested page title contains invalid characters: “$invalid_char”.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-EmptyTitle', wikiuser,
                            'The requested page title is empty or contains only the name of a namespace.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-ReadForbidden', wikiuser,
                            'You do not have the permisson to view this page.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-EditForbidden', wikiuser, 'You do not have the permisson to edit this page.',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-EditForbidden-4', wikiuser,
                            'You do not have the permisson to edit this page for the following reasons:\n'
                            '* This page provides interface text for the software on this wiki, '
                            'and is protected to prevent abuse.', _COMMENT, False)

    api.submit_page_content(4, 'Message-EditForbidden-16', wikiuser,
                            'You do not have the permisson to edit this page for the following reasons:\n'
                            '* This page provides interface text for the software on this wiki, '
                            'and is protected to prevent abuse.', _COMMENT, False)

    api.submit_page_content(4, 'Message-CreateForbidden', wikiuser,
                            'You do not have the permisson to create this page.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-CreateForbidden-4', wikiuser,
                            'You do not have the permisson to create this page for the following reasons:\n'
                            '* This page provides interface text for the software on this wiki, '
                            'and is protected to prevent abuse.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-CreateForbidden-16', wikiuser,
                            'You do not have the permisson to create this page for the following reasons:\n'
                            '* This page provides interface text for the software on this wiki, '
                            'and is protected to prevent abuse.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-NoPage', wikiuser,
                            f'{project_name} does not have a {{{{NAMESPACE_NAME}}}} page with this name.\n\n'
                            f'Return to [[{main_page}]].', _COMMENT, False)

    api.submit_page_content(4, 'Message-EditNotice-0', wikiuser, 'This is the edit notice for main namespace.',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-EditNotice-4', wikiuser,
                            '<div class="alert alert-warning text-center" role="alert">'
                            'Be carefull as changes made to this page will impact all users.'
                            '</div>',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-EditNotice-16', wikiuser,
                            '<div class="alert alert-warning text-center" role="alert">'
                            'Be carefull as changes made to this page will impact all users.'
                            '</div>',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-InvalidRevisionID', wikiuser,
                            'Revision #$revision_id of page “{{PAGE_TITLE}}” does not exist.\n\n'
                            'This usually happens when following a link to a deleted revision. '
                            'You can find more information in the '
                            '[[Special:Journal/deleted revisions|deletion journal]].',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-LoginDisclaimer', wikiuser,
                            f'You must have cookies enabled to log in to {project_name}.', _COMMENT, False)

    api.submit_page_content(4, 'Message-AlreadyLoggedIn', wikiuser,
                            'You are already logged in as {{USERNAME}}. '
                            'If you want to connect as another user, please first log out.',
                            _COMMENT, False)

    api.submit_page_content(4, 'Message-LogoutConfirm', wikiuser, 'Do you want to log out?', _COMMENT, False)

    api.submit_page_content(4, 'Message-LoggedOut', wikiuser,
                            '**You are now logged out.**\n\n'
                            'Note that some pages may continue to be displayed as if you were still logged in, '
                            'until you clear your browser cache.\n\n'
                            f'Return to [[{main_page}]].',
                            _COMMENT, False)

    api.submit_page_content(4, 'Common.css', wikiuser, '/* Put custom CSS in here. */', _COMMENT, False)

    api.submit_page_content(4, 'Common.js', wikiuser, '/* Put custom JavaScript in here. */', _COMMENT, False)

    api.submit_page_content(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE, wikiuser,
                            'This is the main page of TestWiki.', _COMMENT, False)

    logging.info('Done.')

    return SUCCESS
