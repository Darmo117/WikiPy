import typing as typ

import django.template as dj_template
import django.utils.safestring as dj_safe

from . import wpy_tags
from .. import settings, models, special_pages, page_context
from ..api import titles as api_titles, datetime as api_dt

register = dj_template.Library()


@register.simple_tag
def diff_format(line: str, indices: typ.List[typ.Tuple[int, int]], inserted: bool):
    tag = 'ins' if inserted else 'del'
    for start, end in reversed(indices):
        line = f'{line[:start]}<{tag} class="wpy-diff-change">{line[start:end]}</{tag}>{line[end:]}'
    return dj_safe.mark_safe(line)


@register.inclusion_tag('WikiPy/tags/diff-header.html', takes_context=True)
def diff_header(context: page_context.TemplateContext, revision: models.PageRevision, previous: bool,
                show_nav_link: bool):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    current_user = wpy_context.user
    language = wpy_context.language
    skin = wpy_context.skin
    current_title = wpy_context.page.full_title
    page_title = api_titles.get_full_page_title(revision.page.namespace_id, revision.page.title)
    text = language.translate('special.page_differences.diff_header.' + ('previous_diff' if previous else 'next_diff'))

    page_link = skin.format_internal_link(language, current_title, page_title)
    edit_link = wpy_tags.wpy_edit_link(context, revision, ignore_revision_id=True)
    history_link = wpy_tags.wpy_history_link(context, revision)
    if current_user.can_edit_page(revision.page.namespace_id, revision.page.title)[0]:
        page_link += ' ({} {})'.format(edit_link, history_link)
    else:
        page_link += ' ({})'.format(history_link)

    revision_date = api_dt.format_datetime(revision.date, current_user, language)
    revision_link = skin.format_internal_link(language, current_title, page_title, revision_date, page_title,
                                              url_params={'revision_id': revision.id})
    revision_link += ' ({})'.format(wpy_tags.wpy_edit_link(context, revision, ignore_revision_id=False))

    user_link = wpy_tags.wpy_user_link(context, revision.author.username, hidden=revision.author_hidden)

    comment = wpy_tags.wpy_revision_tags(context, revision)
    if revision.comment:
        if comment:
            comment += ' '
        comment += wpy_tags.wpy_revision_comment(context, revision.comment, revision.comment_hidden)

    actions = ''
    if current_user.has_right(settings.RIGHT_DELETE_REVISIONS):
        actions = wpy_tags.wpy_show_hide_revision_link(context, revision)

    if show_nav_link:
        revision_id1 = None
        revision_id2 = None
        if previous:
            target_revision = revision.get_previous(ignore_hidden=not wpy_context.user_can_hide)
            if target_revision:
                revision_id1 = target_revision.id
                revision_id2 = revision.id
        else:
            target_revision = revision.get_next(ignore_hidden=not wpy_context.user_can_hide)
            if target_revision:
                revision_id1 = revision.id
                revision_id2 = target_revision.id

        if target_revision:
            title = api_titles.get_full_page_title(-1, special_pages.get_special_page_for_id(
                'page_differences').get_title())
            title += f'/{revision_id1}/{revision_id2}'
            link = skin.format_internal_link(language, current_title, title, text, title, no_red_link=True)
        else:
            link = text
    else:
        link = ''

    return {
        'page_link': dj_safe.mark_safe(page_link),
        'revision_link': dj_safe.mark_safe(revision_link),
        'user_link': dj_safe.mark_safe(user_link),
        'comment': dj_safe.mark_safe(comment),
        'actions': dj_safe.mark_safe(actions),
        'nav_link': dj_safe.mark_safe(link),
    }
