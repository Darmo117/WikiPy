import logging
import os

import django.contrib.auth.models as dj_models

from WikiPy_app import models

WIKI_USER_NAME = 'WikiPy'
_PASSWORD = os.getenv('WIKIPY_USER_PASSWD', default='password')


def setup():
    logging.info('Setting up default pages…')

    wikiuser = dj_models.User.objects.create_user(username=WIKI_USER_NAME, password=_PASSWORD)
    wikiuser.save()
    models.UserData(user=wikiuser).save()
    models.UserGroupRel(user=wikiuser, group_id='administrator').save()

    bad_title_page = models.Page(namespace_id=4, title='Message-BadTitle')
    bad_title_page.save()
    models.PageRevision(page=bad_title_page,
                        content='The requested page title contains invalid characters: “%(invalid_char)”.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    empty_title_page = models.Page(namespace_id=4, title='Message-EmptyTitle')
    empty_title_page.save()
    models.PageRevision(page=empty_title_page,
                        content='The requested page title is empty or contains only the name of a namespace.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    no_read_access_page = models.Page(namespace_id=4, title='Message-ReadForbidden')
    no_read_access_page.save()
    models.PageRevision(page=no_read_access_page,
                        content='You do not have the permisson to view this page.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    no_read_access_page = models.Page(namespace_id=4, title='Message-EditForbidden')
    no_read_access_page.save()
    models.PageRevision(page=no_read_access_page,
                        content='You do not have the permisson to edit this page.',
                        author=wikiuser).save()

    no_read_access_page = models.Page(namespace_id=4, title='Message-EditForbidden-4')
    no_read_access_page.save()
    models.PageRevision(page=no_read_access_page,
                        content='You do not have the permisson to edit this page for the following reasons:\n'
                                '* This page provides interface text for the software on this wiki, '
                                'and is protected to prevent abuse.',
                        author=wikiuser).save()

    no_read_access_page = models.Page(namespace_id=4, title='Message-CreateForbidden')
    no_read_access_page.save()
    models.PageRevision(page=no_read_access_page,
                        content='You do not have the permisson to create this page.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    no_edit_access_page = models.Page(namespace_id=4, title='Message-CreateForbidden-4')
    no_edit_access_page.save()
    models.PageRevision(page=no_edit_access_page,
                        content='You do not have the permisson to create this page for the following reasons:\n'
                                '* This page provides interface text for the software on this wiki, '
                                'and is protected to prevent abuse.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    no_page = models.Page(namespace_id=4, title='Message-NoPage')
    no_page.save()
    models.PageRevision(page=no_page,
                        content='%(project_name) does not have a %(namespace_name) page with this name.\n\n'
                                'Return to [[%(home_page)]].',
                        author=wikiuser).save()

    no_page_history = models.Page(namespace_id=4, title='Message-NoPageHistory')
    no_page_history.save()
    models.PageRevision(page=no_page_history,
                        content='This page does not have any history.',
                        author=wikiuser).save()

    main_ns_editnotice = models.Page(namespace_id=4, title='Message-EditNotice-0')
    main_ns_editnotice.save()
    models.PageRevision(page=main_ns_editnotice,
                        content='This is the edit notice for main namespace.',
                        author=wikiuser).save()

    # TODO use settings
    main_page = models.Page(namespace_id=-3, title='Main Page')
    main_page.save()
    models.PageRevision(page=main_page,
                        content='This is the main page of TestWiki.',
                        author=wikiuser).save()

    logging.info('Default pages set up.')
