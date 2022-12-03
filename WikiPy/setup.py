import logging
import os

import django.conf as dj_conf
import django.contrib.auth as dj_auth
import django.core.handlers.wsgi as dj_wsgi
import django.utils.crypto as dj_crypto

from . import settings, apps, models, page_handlers
from .api import titles as api_titles, pages as api_pages, users as api_users, errors as api_errors

WIKI_USER_NAME = 'WikiPy'
_COMMENT = 'Wiki setup.'

INVALID_USERNAME = 'invalid_username'
INVALID_PASSWORD = 'invalid_password'
INVALID_EMAIL = 'invalid_email'
INVALID_SECRET_KEY = 'invalid_secret_key'
SUCCESS = 'ok'


def are_pages_setup() -> bool:
    # Check whether the setup user is created
    return dj_auth.get_user_model().objects.filter(username=WIKI_USER_NAME).count() == 1


def generate_secret_key_file() -> bool:
    path = os.path.join(dj_conf.settings.BASE_DIR, apps.WikiPyConfig.name, 'SETUP_SECRET_KEY')
    if not os.path.exists(path):
        secret_key = dj_crypto.get_random_string(length=20)
        with open(path, mode='w', encoding='UTF-8') as f:
            f.write(secret_key)
            f.flush()
        return True
    return False


def delete_key_file():
    path = os.path.join(dj_conf.settings.BASE_DIR, apps.WikiPyConfig.name, 'SETUP_SECRET_KEY')
    os.remove(path)


def _create_page(request: dj_wsgi.WSGIRequest, namespace_id: int, title: str, user: models.User, content: str):
    context, _ = page_handlers.ActionHandler(
        action=page_handlers.ACTION_EDIT,
        request=request,
        namespace_id=namespace_id,
        title=title,
        user=user,
        language=settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE),
        skin_id=user.data.skin,
        redirect_enabled=False
    ).get_page_context()
    # No need to check for errors
    api_pages.submit_page_content(context, namespace_id, title, content, _COMMENT, False, performer=user)


def setup(request: dj_wsgi.WSGIRequest, username: str, password: str, email: str, secret_key: str) -> str:
    main_page = api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)
    project_name = settings.PROJECT_NAME

    logging.info('Creating administrator…')

    try:
        with open('WikiPy/SETUP_SECRET_KEY', mode='r', encoding='UTF-8') as f:
            setup_secret_key = f.readline()
            if secret_key != setup_secret_key:
                return INVALID_SECRET_KEY
    except FileNotFoundError:
        raise FileNotFoundError('no secret key file defined')

    try:
        admin = api_users.create_user(username, password=password, email=email)
    except (api_errors.InvalidUsernameError, api_errors.DuplicateUsernameError):
        return INVALID_USERNAME
    except api_errors.InvalidPasswordError:
        return INVALID_PASSWORD
    except api_errors.InvalidEmailError:
        return INVALID_EMAIL

    api_users.add_user_to_group(admin, settings.GROUP_AUTOPATROLLED, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_PATROLLERS, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_ADMINISTRATORS, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_INTERFACE_ADMINISTRATORS, performer=None, auto=True,
                                reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_MESSAGE_ADMINISTRATORS, performer=None, auto=True,
                                reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_FILE_MANAGERS, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_USER_CHECKERS, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_ABUSE_FILTER_MODIFIERS, performer=None, auto=True,
                                reason=_COMMENT)
    api_users.add_user_to_group(admin, settings.GROUP_GROUPS_MANAGERS, performer=None, auto=True, reason=_COMMENT)

    logging.info('Done.')

    logging.info('Setting up default pages…')

    password = dj_auth.get_user_model().objects.make_random_password(length=100)
    wiki_user = api_users.create_user(WIKI_USER_NAME, password=password, ignore_email=True)
    api_users.add_user_to_group(wiki_user, settings.GROUP_ADMINISTRATORS, performer=None, auto=True, reason=_COMMENT)
    api_users.add_user_to_group(wiki_user, settings.GROUP_BOTS, performer=None, auto=True, reason=_COMMENT)

    # TODO translate default texts

    _create_page(request, settings.WIKIPY_NS.id, 'Message-ReadForbidden', wiki_user,
                 'You do not have the permisson to view this page.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, f'Message-EditForbidden-{settings.WIKIPY_NS.id}', wiki_user,
                 'You do not have the permisson to edit this page for the following reasons:\n'
                 '* This page provides interface text for the software on this wiki, '
                 'and is protected to prevent abuse.')

    _create_page(request, settings.WIKIPY_NS.id, f'Message-EditForbidden-{settings.GADGET_NS.id}', wiki_user,
                 'You do not have the permisson to edit this page for the following reasons:\n'
                 '* This page provides interface text for the software on this wiki, '
                 'and is protected to prevent abuse.')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-CreateForbidden', wiki_user,
                 'You do not have the permisson to create this page.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, f'Message-CreateForbidden-{settings.WIKIPY_NS.id}', wiki_user,
                 'You do not have the permisson to create this page for the following reasons:\n'
                 '* This page provides interface text for the software on this wiki, '
                 'and is protected to prevent abuse.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, f'Message-CreateForbidden-{settings.GADGET_NS.id}', wiki_user,
                 'You do not have the permisson to create this page for the following reasons:\n'
                 '* This page provides interface text for the software on this wiki, '
                 'and is protected to prevent abuse.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-NoPage', wiki_user,
                 f'{project_name} does not have a {{{{NAMESPACE_NAME}}}} page with this name.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-NoSpecialPage', wiki_user,
                 f'**This special page does not exist.**\n\n'
                 f'A list of valid special pages can be found at [[Special:Special pages]].\n\n'
                 f'Go back to [[TestWiki:Main Page]].')

    _create_page(request, settings.WIKIPY_NS.id, f'Message-EditNotice-{settings.MAIN_NS.id}', wiki_user,
                 'This is the edit notice for main namespace.')  # TEMP

    _create_page(request, settings.WIKIPY_NS.id, 'Message-InvalidRevisionID', wiki_user,
                 'Revision #$revision_id of page “{{FULL_PAGE_TITLE}}” does not exist.\n\n'
                 'This usually happens when following a link to a deleted revision. '
                 'You can find more information in the '
                 '[[Special:Journals/deleted revisions|deletion journal]].')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-LoginDisclaimer', wiki_user,
                 f'You must have cookies enabled to log in to {project_name}.')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-AlreadyLoggedIn', wiki_user,
                 'You are already logged in as {{USERNAME}}. '
                 'If you want to connect as another user, please first log out.')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-LogoutConfirm', wiki_user, 'Do you want to log out?')

    _create_page(request, settings.WIKIPY_NS.id, 'Message-LoggedOut', wiki_user,
                 '**You are now logged out.**\n\n'
                 'Note that some pages may continue to be displayed as if you were still logged in, '
                 'until you clear your browser cache.\n\n'
                 f'Return to the [[{main_page}|main page]].')

    _create_page(request, settings.WIKIPY_NS.id, 'Common.css', wiki_user, '/* Put custom CSS in here. */')

    _create_page(request, settings.WIKIPY_NS.id, 'Common.js', wiki_user, '/* Put custom JavaScript in here. */')

    _create_page(request, settings.WIKIPY_NS.id, 'SideMenus', wiki_user,
                 '* navigation\n** main_page\n** random_page\n** recent_changes')

    _create_page(request, settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE, wiki_user,
                 f'This is the main page of {settings.PROJECT_NAME}.')

    logging.info('Done.')

    return SUCCESS
