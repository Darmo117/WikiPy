import typing as typ

import django.core.paginator as dj_page
import django.shortcuts as dj_scut
import django.template as dj_template
import django.utils.safestring as dj_safe

from .. import api, skins, settings, models, special_pages, page_context

register = dj_template.Library()


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
    if api.page_exists(namespace_id, page_title):
        full_title = api.get_full_page_title(namespace_id, page_title)
        url = dj_scut.reverse('page', args=[full_title]) + '?action=raw'

        if full_title.endswith('.css'):
            return dj_safe.mark_safe(f'<link href="{url}" rel="stylesheet"/>')
        elif full_title.endswith('.js'):
            return dj_safe.mark_safe(f'<script src="{url}"></script>')

    return ''


@register.simple_tag(takes_context=True)
def wpy_render(context: page_context.TemplateContext, wikicode: str):
    return dj_safe.mark_safe(api.render_wikicode(wikicode, context.get('wpy_context').skin_name))


@register.simple_tag(takes_context=True)
def wpy_format_date(context: page_context.TemplateContext, date):
    return dj_safe.mark_safe(api.format_datetime(date, context.get('wpy_context').user))


@register.simple_tag(takes_context=True)
def wpy_user_link(context: page_context.TemplateContext, username: str, ignore_title: bool = False,
                  only_username: bool = False, full: bool = False, no_red_link: bool = False, hidden: bool = False):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    current_user = wpy_context.user
    user_page_title = api.get_full_page_title(6, username)
    current_page_title = wpy_context.full_page_title

    skin = skins.get_skin(wpy_context.skin_name)

    res = ''

    if not hidden or wpy_context.user_can_hide:
        user_link = skin.format_internal_link(api, wpy_context.full_page_title if not ignore_title else '',
                                              user_page_title, text=username, tooltip=user_page_title,
                                              no_red_link=no_red_link)

        if only_username:
            res = user_link
        else:
            talk_page_title = api.get_full_page_title(7, username)
            contribs_page_title = api.get_full_page_title(-1, 'Contributions/' + username)
            links = [
                skin.format_internal_link(api, current_page_title, talk_page_title,
                                          text=settings.i18n.trans('link.talk'), tooltip=talk_page_title),
                skin.format_internal_link(api, current_page_title, contribs_page_title,
                                          text=settings.i18n.trans('link.contributions'),
                                          tooltip=contribs_page_title)
            ]
            if current_user.has_right(settings.RIGHT_BLOCK_USERS):
                special_page = special_pages.get_special_page_for_id('block')
                page_title = api.get_full_page_title(-1, special_page.get_title())
                page_title += '/' + username
                links.append(skin.format_internal_link(api, current_page_title, page_title,
                                                       text=settings.i18n.trans('link.block'),
                                                       tooltip=page_title))
            if full:
                # TODO journal des blocages, téléversements, journaux, contributions de l’utilisateur supprimées,
                # gestion des droits de l’utilisateur, suppression de masse, journal des abus
                pass

            res = f'{user_link} ({" | ".join(links)})'

    if hidden:
        if not wpy_context.user_can_hide:
            res = settings.i18n.trans('revision.hidden_username.label')
        tooltip = settings.i18n.trans('revision.hidden_username.tooltip')
        res = f'<span class="wpy-hidden-revision-author" title="{tooltip}">{res}</span>'

    return dj_safe.mark_safe(res)


@register.simple_tag(takes_context=True)
def wpy_revision_comment(context: page_context.TemplateContext, comment: str, hidden: bool = False):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    res = ''

    if not hidden or wpy_context.user_can_hide:
        classes = ['wpy-revision-comment']
        tooltip = ''
        if hidden:
            classes.append('wpy-hidden-revision-comment')
            tooltip = settings.i18n.trans('revision.hidden_comment.tooltip')
        res = f'<span class="{" ".join(classes)}" title="{tooltip}">{comment}</span>'

    return dj_safe.mark_safe(res)


@register.simple_tag
def wpy_page_size_tag(total_size: int):
    text = settings.i18n.trans('tag.page_size.label', content_size=total_size)
    return dj_safe.mark_safe(f'<span class="badge badge-light wpy-page-size-tag">{text}</span>')


@register.simple_tag(takes_context=True)
def wpy_revision_tags(context: dict, revision: models.PageRevision, get_tag: str = None):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    tags = []

    if get_tag == 'new' or not get_tag and revision.has_created_page:
        tags.append(_render_tag('page_creation'))
    if get_tag == 'minor' or not get_tag and revision.minor:
        tags.append(_render_tag('minor_edit'))
    if get_tag == 'bot' or not get_tag and revision.is_bot_edit:
        tags.append(_render_tag('bot_edit'))
    if get_tag == 'current' or not get_tag and not revision.get_next(ignore_hidden=not wpy_context.user_can_hide):
        tags.append(_render_tag('current_revision'))

    return dj_safe.mark_safe(' '.join(tags))


def _render_tag(tag_id: str):
    colors = {
        'page_creation': 'badge-primary',
        'minor_edit': 'badge-light',
        'bot_edit': 'badge-secondary',
        'current_revision': 'badge-info',
    }
    text = settings.i18n.trans(f'tag.{tag_id}.label')
    tooltip = settings.i18n.trans(f'tag.{tag_id}.tooltip')
    return f'<abbr class="badge {colors[tag_id]} wpy-tag wpy-{tag_id}-tag" title="{tooltip}">{text}</abbr>'


@register.simple_tag
def wpy_diff_size_tag(diff_size: int, total_size: int = None):
    classes = ['badge', 'wpy-diff-size-tag']
    if total_size is not None:
        sign = '+' if diff_size >= 0 else '−'
    else:
        sign = '±'
    if abs(diff_size) > settings.DIFF_SIZE_TAG_IMPORTANT:
        classes.append('wpy-diff-size-tag-important')
    if diff_size > 0:
        classes.append('wpy-diff-size-tag-positive')
        classes.append('badge-success')
    elif diff_size < 0:
        classes.append('wpy-diff-size-tag-negative')
        classes.append('badge-danger')
    else:
        classes.append('wpy-diff-size-tag-zero')
        classes.append('badge-secondary')
    if total_size is not None:
        title = settings.i18n.trans('tag.diff_size.tooltip', content_size=total_size)
    else:
        title = ''
    return dj_safe.mark_safe(f'<span class="{" ".join(classes)}" title="{title}">{sign}{abs(diff_size)}</span>')


@register.simple_tag(takes_context=True)
def wpy_edit_link(context: page_context.TemplateContext, revision: models.PageRevision, ignore_revision_id: bool):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    skin = skins.get_skin(wpy_context.skin_name)
    page_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
    text = f'<i class="fa fa-edit"></i>'
    tooltip = settings.i18n.trans('link.edit.tooltip')
    link = skin.format_internal_link(api, wpy_context.full_page_title, page_title, text=text, tooltip=tooltip,
                                     action='edit', revision_id=revision.id if not ignore_revision_id else None)

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_history_link(context: page_context.TemplateContext, revision: models.PageRevision):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    skin = skins.get_skin(wpy_context.skin_name)
    page_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
    text = f'<i class="fa fa-history"></i>'
    tooltip = settings.i18n.trans('link.history.tooltip')
    link = skin.format_internal_link(api, wpy_context.full_page_title, page_title, text=text, tooltip=tooltip,
                                     action='history')

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_show_hide_revision_link(context: page_context.TemplateContext, revision: models.PageRevision):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    skin = skins.get_skin(wpy_context.skin_name)

    hidden = revision.text_hidden or revision.author_hidden or revision.comment_hidden
    page_title = api.get_full_page_title(-1, special_pages.get_special_page_for_id('hide_revisions').get_title())

    icon = 'eye' if hidden else 'eye-slash'
    text = f'<i class="fa fa-{icon}"></i>'
    tooltip = settings.i18n.trans('link.show_hide.tooltip')
    link = skin.format_internal_link(api, wpy_context.full_page_title, page_title, text=text, tooltip=tooltip,
                                     revision_ids=revision.id)

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_diff_link(context: page_context.TemplateContext, revision: models.PageRevision, against: str,
                  show_nav_link: bool = False):
    values = {
        'previous': 'difference',
        'current': 'current',
        'next': 'difference',
    }
    if against not in values:
        raise ValueError(f'invalid value "{against}"')

    wpy_context: page_context.PageContext = context.get('wpy_context')
    skin = skins.get_skin(wpy_context.skin_name)
    text = '<i class="fa fa-not-equal"></i>'
    tooltip = settings.i18n.trans(f'link.{values[against]}.tooltip')
    nav_text = settings.i18n.trans(f'link.{against}_revision')
    current_title = wpy_context.full_page_title
    target_revision = None
    revision_id1 = None
    revision_id2 = None

    if against == 'previous':
        target_revision = revision.get_previous(ignore_hidden=not wpy_context.user_can_hide)
        if target_revision:
            revision_id1 = target_revision.id
            revision_id2 = revision.id
    elif against == 'next':
        target_revision = revision.get_next(ignore_hidden=not wpy_context.user_can_hide)
        if target_revision:
            revision_id1 = revision.id
            revision_id2 = target_revision.id
    elif not revision.text_hidden or wpy_context.user_can_hide:
        target_revision = revision.page.get_latest_revision()
        revision_id1 = revision.id
        revision_id2 = target_revision.id

    if target_revision and revision_id1 != revision_id2:
        title = api.get_full_page_title(-1, special_pages.get_special_page_for_id('page_differences').get_title())
        title += f'/{revision_id1}/{revision_id2}'
        link = skin.format_internal_link(api, current_title, title, text, tooltip, no_red_link=True)
    else:
        link = text

    if show_nav_link:
        if target_revision and revision_id1 != revision_id2:
            revision_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
            nav_link = skin.format_internal_link(api, current_title, revision_title, nav_text, revision_title,
                                                 no_red_link=True, revision_id=target_revision.id)
        else:
            nav_link = nav_text
        link = f'{nav_link} ({link})'

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_inner_link(context: page_context.TemplateContext, namespace_id: int, page_title: str, text: str = None,
                   tooltip: str = None, no_red_link: bool = False, css_classes: str = None,
                   ignore_current_title: bool = False, **url_params):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    current_title = wpy_context.full_page_title if not ignore_current_title else ''
    skin = skins.get_skin(wpy_context.skin_name)
    if namespace_id == -1:
        sp = special_pages.get_special_page_for_id(page_title)
        page_title = sp.get_title()
        text = sp.display_title
        tooltip = text
    full_title = api.get_full_page_title(namespace_id, page_title)
    if not tooltip:
        tooltip = full_title
    classes = css_classes.split() if css_classes else []
    link = skin.format_internal_link(api, current_title, full_title, text, tooltip,
                                     no_red_link=no_red_link, css_classes=classes, **url_params)
    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_header_link(context: page_context.TemplateContext, link_type: str, special_page_id: str = None,
                    no_redirect: bool = False, add_return_to: bool = False, no_red_link: bool = False,
                    css_classes: str = None, special_page_subtitle: str = None, no_access_key: bool = False):
    if link_type not in ['read', 'talk', 'edit', 'create', 'source', 'history', 'special', 'user_page', 'user_talk']:
        raise ValueError(f'invalid link type "{link_type}"')

    wpy_context: page_context.PageContext = context.get('wpy_context')
    access_key = None

    params = {}
    if add_return_to:
        params['return_to'] = wpy_context.full_page_title_url

    if link_type == 'special':
        special_page = special_pages.get_special_page_for_id(special_page_id)
        page_title = api.get_full_page_title(-1, special_page.get_title())
        if special_page_subtitle:
            page_title += '/' + special_page_subtitle
        text = special_page.display_title
        tooltip = text
        icon = {
            'login': ('sign-in-alt', None),
            'logout': ('sign-out-alt', None),
            'contributions': ('puzzle-piece', 'c'),
        }.get(special_page_id)
        if icon:
            text = f'<i class="fa fa-{icon[0]}"></i> ' + text
            access_key = icon[1]
    else:
        page_title = wpy_context.full_page_title
        text = settings.i18n.trans(f'link.header.{link_type}.label')
        tooltip = settings.i18n.trans(f'link.header.{link_type}.tooltip')
        ns_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
        if link_type == 'read':
            ns_id = api.get_base_page_namespace(ns_id)
            text = '<i class="fa fa-book-open"></i> ' + text
            access_key = 'v'
        elif link_type == 'talk':
            ns_id = api.get_talk_page_namespace(ns_id)
            text = '<i class="far fa-comments"></i> ' + text
            access_key = 't'
        elif link_type == 'user_page':
            ns_id = 6
            title = wpy_context.user.username
            text = '<i class="far fa-user"></i> ' + text
            access_key = 'u'
        elif link_type == 'user_talk':
            ns_id = 7
            title = wpy_context.user.username
            text = '<i class="far fa-comment"></i> ' + text
            access_key = 'w'
        page_title = api.get_full_page_title(ns_id, title)

        if link_type in ['edit', 'create', 'source']:
            params['action'] = 'edit'
            if isinstance(wpy_context, page_context.RevisionPageContext) and wpy_context.archived:
                if revision := wpy_context.revision:
                    params['revision_id'] = revision.id
            text = '<i class="fa fa-edit"></i> ' + text
            access_key = 'e'
        elif link_type == 'history':
            params['action'] = 'history'
            text = '<i class="fa fa-history"></i> ' + text
            access_key = 'h'

        if no_redirect:
            params['no_redirect'] = '1'

    classes = css_classes.split() if css_classes else []
    skin = skins.get_skin(wpy_context.skin_name)
    link = skin.format_internal_link(api, '', page_title, text=text, tooltip=tooltip, no_red_link=no_red_link,
                                     css_classes=classes, access_key=access_key if not no_access_key else None,
                                     **params)

    return dj_safe.mark_safe(link)


@register.inclusion_tag('WikiPy_app/tags/history-list.html', takes_context=True)
def wpy_history_list(context: page_context.TemplateContext):
    return _revisions_list(context, mode='history')


@register.inclusion_tag('WikiPy_app/tags/contributions-list.html', takes_context=True)
def wpy_contributions_list(context: page_context.TemplateContext):
    return _revisions_list(context, mode='contributions')


def _revisions_list(context: page_context.TemplateContext, mode: str):
    revisions_ = []
    wpy_context: page_context.PageContext = context.get('wpy_context')
    current_user = wpy_context.user
    current_page_title = wpy_context.full_page_title
    paginator = wpy_context.paginator
    page = wpy_context.page
    skin_id = wpy_context.skin_name
    skin = skins.get_skin(skin_id)

    if paginator:
        for revision in paginator.get_page(page).object_list:
            full_title = api.get_full_page_title(revision.page.namespace_id, revision.page.title)
            revision_link = skin.format_internal_link(api, current_page_title, full_title,
                                                      text=api.format_datetime(revision.date, current_user),
                                                      tooltip=full_title, revision_id=revision.id)
            user_link = wpy_user_link(context, revision.author.username)
            revisions_.append((revision, revision_link, user_link))

    return {
        'wpy_context': wpy_context,
        'mode': mode,
        'revisions': revisions_,
        'url_params': context.get('request').GET,
    }


@register.inclusion_tag('WikiPy_app/tags/pagination.html', takes_context=True)
def wpy_paginator(context: typ.Dict[str, typ.Any], top: bool):
    wpy_context: page_context.ListPageContext = context.get('wpy_context')
    paginator = wpy_context.paginator
    page = wpy_context.page
    current_page_title = wpy_context.full_page_title
    url_params = context.get('url_params', {})
    url_params = {k: v for k, v in url_params.items() if k != 'page'}
    url_params['limit'] = paginator.per_page
    skin = skins.get_skin(wpy_context.skin_name)

    first_link, not_at_first = _get_paginator_link('first', current_page_title, paginator, page,
                                                   wpy_context.writing_direction, skin, **url_params)
    prev_link, has_prev = _get_paginator_link('previous', current_page_title, paginator, page,
                                              wpy_context.writing_direction, skin, **url_params)
    next_link, has_next = _get_paginator_link('next', current_page_title, paginator, page,
                                              wpy_context.writing_direction, skin, **url_params)
    last_link, not_at_last = _get_paginator_link('last', current_page_title, paginator, page,
                                                 wpy_context.writing_direction, skin, **url_params)

    position = settings.i18n.trans('pagination.position', page=page, total=paginator.num_pages)

    offset_links = []
    offsets = [25, 50, 100, 250, 500]
    for o in offsets:
        params = dict(url_params)
        params['limit'] = o
        params['page'] = 1
        classes = ['btn', 'btn-light']
        if o == paginator.per_page:
            classes.append('disabled')
        link = skin.format_internal_link(api, current_page_title, current_page_title, text=str(o),
                                         tooltip=current_page_title, css_classes=classes, **params)
        offset_links.append(dj_safe.mark_safe(link))

    page_obj = paginator.get_page(page)

    return {
        'first': dj_safe.mark_safe(first_link),
        'previous': dj_safe.mark_safe(prev_link),
        'next': dj_safe.mark_safe(next_link),
        'last': dj_safe.mark_safe(last_link),
        'has_prev': has_prev,
        'has_next': has_next,
        'at_first': not not_at_first,
        'at_last': not not_at_last,
        'numbers': offset_links,
        'start_index': page_obj.start_index(),
        'end_index': page_obj.end_index(),
        'total': paginator.count,
        'page': page,
        'pages_number': paginator.num_pages,
        'position': position,
        'top': top,
    }


def _get_paginator_link(link_type: str, current_page_title: str, paginator: dj_page.Paginator, page: int,
                        writing_direction: str, skin: skins.Skin, **url_params) -> typ.Tuple[str, bool]:
    page_obj = paginator.get_page(page)
    arrows = {
        'previous': ('‹', '›', True, page_obj.has_previous(), page_obj.previous_page_number),
        'next': ('›', '‹', False, page_obj.has_next(), page_obj.next_page_number),
        'first': ('«', '»', True, page > 1, lambda: 1),
        'last': ('»', '«', False, page < paginator.num_pages, lambda: paginator.num_pages),
    }
    arrow_ltr, arrow_rtl, before_text, enabled, page_function = arrows[link_type]
    if writing_direction == 'rtl':
        before_text = not before_text
        arrow = arrow_rtl
    else:
        arrow = arrow_ltr
    text = settings.i18n.trans('pagination.' + link_type, nb_per_page=paginator.per_page)
    if before_text:
        text = arrow + '\u00a0' + text
    else:
        text += '\u00a0' + arrow

    classes = ['page-link']
    if enabled:
        url_params['page'] = page_function()
        return skin.format_internal_link(api, current_page_title, current_page_title, text=text,
                                         tooltip=current_page_title, css_classes=classes, **url_params), True
    return f'<span class="{" ".join(classes)}">{text}</span>', False
