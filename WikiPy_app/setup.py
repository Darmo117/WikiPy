from WikiPy_app import models

WIKI_USER_NAME = 'WikiPy'


def setup():
    wikiuser = models.User(name=WIKI_USER_NAME)
    wikiuser.save()
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
