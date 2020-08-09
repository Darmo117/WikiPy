import django.shortcuts as dj_scut
import django.utils.safestring as dj_safe
from django import template

from .. import api, skins, settings, models, special_pages

register = template.Library()


@register.filter
def wpy_encode_url(page_title: str):
    return api.as_url_title(page_title)


@register.filter
def wpy_page_title(page_title: str, ns_id: int = 0):
    return api.get_full_page_title(ns_id, page_title)


@register.simple_tag
def wpy_translate(key: str, **kwargs):
    return dj_safe.mark_safe(settings.i18n.trans(key, **kwargs))


@register.simple_tag
def wpy_static(namespace_id: int, page_title: str):
    full_title = api.get_full_page_title(namespace_id, page_title)
    return dj_scut.reverse('page', args=[full_title]) + '?action=raw'


@register.simple_tag(takes_context=True)
def wpy_render(context: dict, wikicode: str):
    skin_id = context.get('wpy_user').data.skin
    return dj_safe.mark_safe(api.render_wikicode(wikicode, skin_id))


@register.simple_tag(takes_context=True)
def wpy_format_date(context: dict, date):
    return dj_safe.mark_safe(api.format_datetime(date, context.get('wpy_user')))


@register.simple_tag(takes_context=True)
def wpy_user_link(context: dict, current_page_title: str, username: str, only_username: bool = False):
    user_page_title = api.get_full_page_title(6, username)

    skin = skins.get_skin(context.get('wpy_user').data.skin)
    user_link = skin.format_internal_link(api, current_page_title, user_page_title, text=username,
                                          tooltip=user_page_title)

    if only_username:
        res = user_link
    else:
        talk_page_title = api.get_full_page_title(7, username)
        contribs_page_title = api.get_full_page_title(-1, 'Contributions/' + username)
        talk_link = skin.format_internal_link(api, current_page_title, talk_page_title,
                                              text=settings.i18n.trans('link.talk'), tooltip=talk_page_title)
        contribs_link = skin.format_internal_link(api, current_page_title, contribs_page_title,
                                                  text=settings.i18n.trans('link.contributions'),
                                                  tooltip=contribs_page_title)
        res = f'{user_link} ({talk_link} | {contribs_link})'

    return dj_safe.mark_safe(res)


@register.simple_tag
def wpy_page_size_tag(total_size: int):
    text = settings.i18n.trans('tag.page_size.label', content_size=total_size)
    return dj_safe.mark_safe(f'<span class="wpy-page-size-tag">{text}</span>')


@register.simple_tag
def wpy_minor_edit_tag():
    return _render_tag('minor_edit')


@register.simple_tag
def wpy_page_creation_tag():
    return _render_tag('page_creation')


@register.simple_tag
def wpy_bot_edit_tag():
    return _render_tag('bot_edit')


def _render_tag(tag_id: str):
    text = settings.i18n.trans(f'tag.{tag_id}.label')
    tooltip = settings.i18n.trans(f'tag.{tag_id}.tooltip')
    return dj_safe.mark_safe(f'<span class="wpy-tag wpy-{tag_id}-tag" title="{tooltip}">{text}</span>')


@register.simple_tag
def wpy_diff_size_tag(diff_size: int, total_size: int = None):
    classes = ['wpy-diff-size-tag']
    if total_size is not None:
        sign = '+' if diff_size >= 0 else '−'
    else:
        sign = '±'
    if abs(diff_size) > settings.DIFF_SIZE_TAG_IMPORTANT:
        classes.append('wpy-diff-size-tag-important')
    if diff_size > 0:
        classes.append('wpy-diff-size-tag-positive')
    elif diff_size < 0:
        classes.append('wpy-diff-size-tag-negative')
    else:
        classes.append('wpy-diff-size-tag-zero')
    if total_size is not None:
        title = settings.i18n.trans('tag.diff_size.tooltip', content_size=total_size)
    else:
        title = ''
    return dj_safe.mark_safe(f'<span class="{" ".join(classes)}" title="{title}">{sign}{abs(diff_size)}</span>')


@register.simple_tag(takes_context=True)
def wpy_diff_link(context: dict, revision: models.PageRevision, against: str):
    values = {
        'previous': 'difference',
        'current': 'current',
    }
    if against not in values:
        raise ValueError(f'invalid value "{against}"')

    skin = skins.get_skin(context.get('wpy_user').data.skin)
    page_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
    text = settings.i18n.trans(f'link.{values[against]}')
    if against == 'previous':
        previous_revision = revision.get_previous()
        if not previous_revision:
            return text
        diff = previous_revision.id
    else:
        diff = revision.page.get_latest_revision().id
        if diff == revision.id:
            return text
    link = skin.format_internal_link(api, context.get('full_page_title'), page_title, text, page_title,
                                     revision_id=revision.id, diff=diff)
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_inner_link(context: dict, namespace_id: int, page_title: str, text: str = None, tooltip: str = None,
                   no_red_link: bool = False, **url_params):
    skin = skins.get_skin(context.get('wpy_user').data.skin)
    full_title = api.get_full_page_title(namespace_id, page_title)
    if not tooltip:
        tooltip = full_title
    link = skin.format_internal_link(api, context.get('full_page_title'), full_title, text, tooltip,
                                     no_red_link=no_red_link, **url_params)
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_header_link(context: dict, link_type: str, special_page_id: str = None, no_redirect: bool = False,
                    add_return_to: bool = False):
    if link_type not in ['read', 'talk', 'edit', 'create', 'source', 'history', 'special']:
        raise ValueError(f'invalid link type "{link_type}"')

    params = {}
    if add_return_to:
        params['return_to'] = context['full_page_title_url']

    if link_type == 'special':
        special_page = special_pages.get_special_page_for_id(special_page_id)
        page_title = api.get_full_page_title(-1, special_page.get_title())
        text = special_page.display_title
        tooltip = text
    else:
        page_title = context.get('full_page_title')
        text = settings.i18n.trans(f'link.header.{link_type}.label')
        tooltip = settings.i18n.trans(f'link.header.{link_type}.tooltip')
        ns_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
        if link_type == 'read':
            ns_id = api.get_base_page_namespace(ns_id)
        elif link_type == 'talk':
            ns_id = api.get_talk_page_namespace(ns_id)
        page_title = api.get_full_page_title(ns_id, title)

        if link_type in ['edit', 'create', 'source']:
            params['action'] = 'edit'
        elif link_type == 'history':
            params['action'] = 'history'
        if no_redirect:
            params['no_redirect'] = '1'

    skin = skins.get_skin(context.get('wpy_user').data.skin)
    link = skin.format_internal_link(api, '', page_title, text=text, tooltip=tooltip, **params)

    return dj_safe.mark_safe(link)


@register.inclusion_tag('WikiPy_app/tags/contributions-list.html', takes_context=True)
def wpy_contributions_list(context: dict, mode: str):
    revisions_ = []
    current_user = context.get('wpy_user')
    current_page_title = context.get('full_page_title')
    paginator = context.get('paginator')
    page = context.get('page')
    skin = skins.get_skin(current_user.data.skin)

    if paginator:
        for revision in paginator.get_page(page).object_list:
            full_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
            revision_link = skin.format_internal_link(api, current_page_title, full_title,
                                                      text=api.format_datetime(revision.date, current_user),
                                                      tooltip=full_title, revision_id=revision.id)
            user_link = wpy_user_link(context, current_page_title, revision.author.username)
            revisions_.append((revision, revision_link, user_link))

    return {
        'mode': mode,
        'revisions': revisions_,
        'user_can_hide': current_user.has_right(settings.RIGHT_HIDE_REVISIONS),
        'wpy_user': current_user,
        'current_page_title': current_page_title,
        'url_params': context.get('request').GET,
        'paginator': paginator,
        'page': page,
    }


@register.simple_tag(takes_context=True)
def wpy_paginator(context: dict):
    paginator = context.get('paginator')
    page = context.get('page')
    current_page_title = context.get('current_page_title')
    url_params = context.get('url_params', {})
    url_params = {k: v for k, v in url_params.items()}
    url_params['limit'] = paginator.per_page
    skin = skins.get_skin(context.get('wpy_user').data.skin)

    prev_text = '«\u00a0' + settings.i18n.trans('link.pagination.previous', nb_per_page=paginator.per_page)
    next_text = settings.i18n.trans('link.pagination.next', nb_per_page=paginator.per_page) + '\u00a0»'
    page_obj = paginator.get_page(page)
    if page_obj.has_previous():
        url_params['page'] = page_obj.previous_page_number()
        prev_link = skin.format_internal_link(api, current_page_title, current_page_title, text=prev_text,
                                              tooltip=current_page_title, **url_params)
    else:
        prev_link = prev_text
    if page_obj.has_next():
        url_params['page'] = page_obj.next_page_number()
        next_link = skin.format_internal_link(api, current_page_title, current_page_title, text=next_text,
                                              tooltip=current_page_title, **url_params)
    else:
        next_link = next_text

    offset_links = []
    offsets = [25, 50, 100, 250, 500]
    for o in offsets:
        params = dict(url_params)
        params['limit'] = o
        params['page'] = 1
        if o == paginator.per_page:
            link = str(o)
        else:
            link = skin.format_internal_link(api, current_page_title, current_page_title, text=str(o),
                                             tooltip=current_page_title, **params)
        offset_links.append(link)

    paginator = f'{prev_link} | {next_link} ({" | ".join(offset_links)})'

    return dj_safe.mark_safe(paginator)
