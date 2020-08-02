from django import template
from .. import api, skins, settings

register = template.Library()


@register.filter
def wpy_encode_url(page_title: str):
    return api.as_url_title(page_title)


@register.filter
def wpy_page_title(page_title: str, ns_id: int = 0):
    return api.get_full_page_title(ns_id, page_title)


@register.inclusion_tag('WikiPy_app/tags/url.html')
def wpy_user_link(user, username: str, only_username: bool = False):
    user_page_title = api.get_full_page_title(6, username)
    talk_page_title = api.get_full_page_title(7, username)
    contribs_page_title = api.get_full_page_title(-1, 'Contributions/' + username)

    skin = skins.get_skin(user.data.skin)
    user_link = skin.get_internal_link(api, user_page_title, username)
    talk_link = skin.get_internal_link(api, talk_page_title, settings.i18n.trans('link.talk.label'))
    contribs_link = skin.get_internal_link(api, contribs_page_title, settings.i18n.trans('link.contributions.label'))

    return {'link': f'{user_link} ({talk_link} | {contribs_link})'}


@register.inclusion_tag('WikiPy_app/tags/url.html')
def wpy_internal_link(user, page_title: str, text: str, base: bool = False, talk: bool = False, edit: bool = False,
                      history: bool = False, noredirect: bool = False):
    if history + edit + talk + base > 1:
        raise ValueError('edit and history cannot be true at the same time')

    ns_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
    if base:
        ns_id = api.get_base_page_namespace(ns_id)
    if talk:
        ns_id = api.get_talk_page_namespace(ns_id)
    page_title = api.get_full_page_title(ns_id, title)

    params = {}
    if edit:
        params['action'] = 'edit'
    if history:
        params['action'] = 'history'
    if noredirect:
        params['noredirect'] = '1'

    skin = skins.get_skin(user.data.skin)
    link = skin.get_internal_link(api, page_title, text, **params)

    return {'link': link}
