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
def wpy_page_title(page_title: str, ns_id: int = settings.MAIN_NS.id):
    return api.get_full_page_title(ns_id, page_title)


@register.simple_tag(takes_context=True)
def wpy_translate(context: page_context.TemplateContext, key: str, **kwargs):
    return dj_safe.mark_safe(context.get('wpy_context').language.translate(key, **kwargs))


@register.simple_tag
def wpy_static(namespace_id: int, page_title: str):
    if api.page_exists(namespace_id, page_title):
        full_title = api.get_full_page_title(namespace_id, page_title)
        url = dj_scut.reverse('wikipy:page', args=[full_title]) + '?action=raw'

        if full_title.endswith('.css'):
            return dj_safe.mark_safe(f'<link href="{url}" rel="stylesheet"/>')
        elif full_title.endswith('.js'):
            return dj_safe.mark_safe(f'<script src="{url}"></script>')

    return ''


@register.simple_tag(takes_context=True)
def wpy_render(context: page_context.TemplateContext, wikicode: str):
    return dj_safe.mark_safe(api.render_wikicode(wikicode, context.get('wpy_context')))


@register.simple_tag(takes_context=True)
def wpy_format_date(context: page_context.TemplateContext, date):
    return dj_safe.mark_safe(api.format_datetime(date, context.get('wpy_context').user))


@register.simple_tag(takes_context=True)
def wpy_user_link(context: page_context.TemplateContext, username: str, ignore_title: bool = False,
                  only_username: bool = False, full: bool = False, no_red_link: bool = False, hidden: bool = False):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    current_user = wpy_context.user
    user_page_title = api.get_full_page_title(settings.USER_NS.id, username)
    current_page_title = wpy_context.page.full_title

    skin = wpy_context.skin

    res = ''

    if not hidden or wpy_context.user_can_hide:
        user_link = skin.format_internal_link(language, wpy_context.page.full_title if not ignore_title else '',
                                              user_page_title, text=username, tooltip=user_page_title,
                                              no_red_link=no_red_link)

        if only_username:
            res = user_link
        else:
            talk_page_title = api.get_full_page_title(settings.USER_TALK_NS.id, username)
            contribs_page_title = api.get_full_page_title(settings.SPECIAL_NS.id, 'Contributions/' + username)
            links = [
                skin.format_internal_link(
                    language,
                    current_page_title, talk_page_title,
                    text=language.translate('link.talk'),
                    tooltip=talk_page_title
                ),
                skin.format_internal_link(
                    language,
                    current_page_title, contribs_page_title,
                    text=language.translate('link.contributions'),
                    tooltip=contribs_page_title
                )
            ]
            if current_user.has_right(settings.RIGHT_BLOCK_USERS):
                special_page = special_pages.get_special_page_for_id('block')
                page_title = api.get_full_page_title(settings.SPECIAL_NS.id, special_page.get_title())
                page_title += '/' + username
                links.append(skin.format_internal_link(language, current_page_title, page_title,
                                                       text=language.translate('link.block'),
                                                       tooltip=page_title))
            if full:
                # TODO journal des blocages, téléversements, journaux, contributions de l’utilisateur supprimées,
                # gestion des droits de l’utilisateur, suppression de masse, journal des abus
                pass

            res = f'{user_link} ({" | ".join(links)})'

    if hidden:
        if not wpy_context.user_can_hide:
            res = language.translate('revision.hidden_username.label')
        tooltip = language.translate('revision.hidden_username.tooltip')
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
            tooltip = wpy_context.language.translate('revision.hidden_comment.tooltip')
        res = f'<span class="{" ".join(classes)}" title="{tooltip}">{comment}</span>'

    return dj_safe.mark_safe(res)


@register.simple_tag(takes_context=True)
def wpy_page_size_tag(context: page_context.TemplateContext, total_size: int):
    text = context.get('wpy_context').language.translate('tag.page_size.label', content_size=total_size)
    return dj_safe.mark_safe(f'<span class="badge badge-light wpy-page-size-tag">{text}</span>')


@register.simple_tag(takes_context=True)
def wpy_revision_tags(context: page_context.TemplateContext, revision: models.PageRevision, get_tag: str = None):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    tags = []

    if get_tag == 'new' or not get_tag and revision.has_created_page:
        tags.append(_render_tag(language, 'page_creation'))
    if get_tag == 'minor' or not get_tag and revision.minor:
        tags.append(_render_tag(language, 'minor_edit'))
    if get_tag == 'bot' or not get_tag and revision.is_bot_edit:
        tags.append(_render_tag(language, 'bot_edit'))
    if get_tag == 'current' or not get_tag and not revision.get_next(ignore_hidden=not wpy_context.user_can_hide):
        tags.append(_render_tag(language, 'current_revision'))

    return dj_safe.mark_safe(' '.join(tags))


def _render_tag(language: settings.i18n.Language, tag_id: str):
    colors = {
        'page_creation': 'badge-primary',
        'minor_edit': 'badge-light',
        'bot_edit': 'badge-secondary',
        'current_revision': 'badge-info',
    }
    text = language.translate(f'tag.{tag_id}.label')
    tooltip = language.translate(f'tag.{tag_id}.tooltip')
    return f'<abbr class="badge {colors[tag_id]} wpy-tag wpy-{tag_id}-tag" title="{tooltip}">{text}</abbr>'


@register.simple_tag(takes_context=True)
def wpy_diff_size_tag(context: page_context.TemplateContext, diff_size: int, total_size: int = None):
    language: settings.i18n.Language = context.get('wpy_context').language
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
        title = language.translate('tag.diff_size.tooltip', content_size=total_size)
    else:
        title = ''
    return dj_safe.mark_safe(f'<span class="{" ".join(classes)}" title="{title}">{sign}{abs(diff_size)}</span>')


@register.simple_tag(takes_context=True)
def wpy_edit_link(context: page_context.TemplateContext, revision: models.PageRevision, ignore_revision_id: bool):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    skin = wpy_context.skin
    page_title = revision.page.full_title
    text = f'<span class="mdi mdi-pencil"></span>'
    tooltip = language.translate('link.edit.tooltip')
    link = skin.format_internal_link(language, wpy_context.page.full_title, page_title, text=text, tooltip=tooltip,
                                     action='edit', revision_id=revision.id if not ignore_revision_id else None)

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_history_link(context: page_context.TemplateContext, revision: models.PageRevision):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    skin = wpy_context.skin
    page_title = revision.page.full_title
    text = f'<span class="mdi mdi-history"></span>'
    tooltip = language.translate('link.history.tooltip')
    link = skin.format_internal_link(language, wpy_context.page.full_title, page_title, text=text, tooltip=tooltip,
                                     action='history')

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_show_hide_revision_link(context: page_context.TemplateContext, revision: models.PageRevision):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    skin = wpy_context.skin

    hidden = revision.text_hidden or revision.author_hidden or revision.comment_hidden
    page_title = api.get_full_page_title(settings.SPECIAL_NS.id,
                                         special_pages.get_special_page_for_id('hide_revisions').get_title())

    icon = 'eye' if hidden else 'eye-off'
    text = f'<span class="mdi mdi-{icon}"></span>'
    tooltip = language.translate('link.show_hide.tooltip')
    link = skin.format_internal_link(language, wpy_context.page.full_title, page_title, text=text, tooltip=tooltip,
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
    language = wpy_context.language
    skin = wpy_context.skin
    text = '<span class="mdi mdi-not-equal-variant"></span>'
    tooltip = language.translate(f'link.{values[against]}.tooltip')
    nav_text = language.translate(f'link.{against}_revision')
    current_title = wpy_context.page.full_title
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
        target_revision = revision.page.latest_revision
        revision_id1 = revision.id
        revision_id2 = target_revision.id

    if target_revision and revision_id1 != revision_id2:
        title = api.get_full_page_title(-1, special_pages.get_special_page_for_id('page_differences').get_title())
        title += f'/{revision_id1}/{revision_id2}'
        link = skin.format_internal_link(language, current_title, title, text, tooltip, no_red_link=True)
    else:
        link = text

    if show_nav_link:
        if target_revision and revision_id1 != revision_id2:
            revision_title = revision.page.full_title
            nav_link = skin.format_internal_link(language, current_title, revision_title, nav_text, revision_title,
                                                 no_red_link=True, revision_id=target_revision.id)
        else:
            nav_link = nav_text
        link = f'{nav_link} ({link})'

    return dj_safe.mark_safe(link)


@register.simple_tag(takes_context=True)
def wpy_inner_link(context: page_context.TemplateContext, namespace_id: int, page_title: str, text: str = None,
                   tooltip: str = None, no_red_link: bool = False, css_classes: str = None,
                   ignore_current_title: bool = False, only_url: bool = False, **url_params):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    language = wpy_context.language
    current_title = wpy_context.page.full_title if not ignore_current_title else ''
    skin = wpy_context.skin
    if namespace_id == settings.SPECIAL_NS.id:
        sp = special_pages.get_special_page_for_id(page_title)
        page_title = sp.get_title()
        text = sp.display_title(language)
        tooltip = text
    full_title = api.get_full_page_title(namespace_id, page_title)
    if tooltip is None:
        tooltip = full_title
    classes = css_classes.split() if css_classes else []
    link = skin.format_internal_link(language, current_title, full_title, text, tooltip, no_red_link=no_red_link,
                                     css_classes=classes, only_url=only_url, **url_params)
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
    language = wpy_context.language
    current_page_title = wpy_context.page.full_title
    paginator = wpy_context.paginator
    skin = wpy_context.skin

    if paginator:
        for revision in paginator.get_page(wpy_context.paginator_page).object_list:
            full_title = revision.page.full_title
            revision_link = skin.format_internal_link(language, current_page_title, full_title,
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
def wpy_paginator(context: page_context.TemplateContext, top: bool):
    wpy_context: page_context.ListPageContext = context.get('wpy_context')
    language = wpy_context.language
    paginator = wpy_context.paginator
    paginator_page = wpy_context.paginator_page
    current_page_title = wpy_context.page.full_title
    url_params = context.get('url_params', {})
    url_params = {k: v for k, v in url_params.items() if k != 'page'}
    url_params['limit'] = paginator.per_page
    skin = wpy_context.skin

    first_link, not_at_first = _get_paginator_link(language, 'first', current_page_title, paginator, paginator_page,
                                                   skin, **url_params)
    prev_link, has_prev = _get_paginator_link(language, 'previous', current_page_title, paginator, paginator_page,
                                              skin, **url_params)
    next_link, has_next = _get_paginator_link(language, 'next', current_page_title, paginator, paginator_page,
                                              skin, **url_params)
    last_link, not_at_last = _get_paginator_link(language, 'last', current_page_title, paginator, paginator_page,
                                                 skin, **url_params)

    position = language.translate('pagination.position', page=paginator_page, total=paginator.num_pages)

    offset_links = []
    offsets = [25, 50, 100, 250, 500]
    for o in offsets:
        params = dict(url_params)
        params['limit'] = o
        params['page'] = 1
        classes = ['btn', 'btn-light']
        if o == paginator.per_page:
            classes.append('disabled')
        link = skin.format_internal_link(language, current_page_title, current_page_title, text=str(o),
                                         tooltip=current_page_title, css_classes=classes, **params)
        offset_links.append(dj_safe.mark_safe(link))

    page_obj = paginator.get_page(paginator_page)

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
        'page': paginator_page,
        'pages_number': paginator.num_pages,
        'position': position,
        'top': top,
        'wpy_context': wpy_context,
    }


def _get_paginator_link(language: settings.i18n.Language, link_type: str, current_page_title: str,
                        paginator: dj_page.Paginator, page: int, skin: skins.Skin, **url_params) \
        -> typ.Tuple[str, bool]:
    page_obj = paginator.get_page(page)
    arrows = {
        # (left arrow, right arrow, before text?, enabled?, page number provider)
        'previous': ('‹', '›', True, page_obj.has_previous(), page_obj.previous_page_number),
        'next': ('›', '‹', False, page_obj.has_next(), page_obj.next_page_number),
        'first': ('«', '»', True, page > 1, lambda: 1),
        'last': ('»', '«', False, page < paginator.num_pages, lambda: paginator.num_pages),
    }
    arrow_ltr, arrow_rtl, before_text, enabled, page_function = arrows[link_type]
    if language.writing_direction == 'rtl':
        before_text = not before_text
        arrow = arrow_rtl
    else:
        arrow = arrow_ltr
    text = language.translate('pagination.' + link_type, nb_per_page=paginator.per_page)
    if before_text:
        text = arrow + '\u00a0' + text
    else:
        text += '\u00a0' + arrow

    classes = ['page-link']
    if enabled:
        url_params['page'] = page_function()
        return skin.format_internal_link(language, current_page_title, current_page_title, text=text,
                                         tooltip=current_page_title, css_classes=classes, **url_params), True
    return f'<span class="{" ".join(classes)}">{text}</span>', False
