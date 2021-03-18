"""
This module defines functions to interact with pages.
"""
import dataclasses
import datetime
import random
import typing as typ

import django.core.paginator as dj_page
import django.db.transaction as dj_db_trans

from . import _diff, errors, titles, users, logs
from .. import settings, models, special_pages, parser, media_backends, util

page_title_validator = models.page_title_validator


# region Get pages


def page_exists(namespace_id: int, title: str, talk: bool = False) -> bool:
    if namespace_id != settings.SPECIAL_NS.id:
        if talk:
            return len(get_messages_for_page(namespace_id, title, ignore_hidden_topics=True)) != 0
        else:
            try:
                page = models.Page.objects.get(namespace_id=namespace_id, title=title)
            except models.Page.DoesNotExist:
                return False
            return page.exists
    return special_pages.get_special_page(titles.get_special_page_title(title)) is not None


def paginate(user: models.User, values: typ.Iterable[typ.Any], url_params: typ.Dict[str, str]) \
        -> typ.Tuple[dj_page.Paginator, int]:
    page = max(1, util.get_param(url_params, 'page', expected_type=int, default=1))
    number_per_page = min(settings.REVISIONS_LIST_PAGE_MAX,
                          max(settings.REVISIONS_LIST_PAGE_MIN,
                              util.get_param(url_params, 'limit', expected_type=int,
                                             default=user.data.default_revisions_list_size)))

    return dj_page.Paginator(values, number_per_page), page


@dataclasses.dataclass(frozen=True)
class SearchResult:
    namespace_id: int
    title: str
    date: datetime.datetime
    message_id: typ.Optional[int]
    snapshot: str


def search(query: str, current_user: models.User, namespaces: typ.Iterable[int], ignore_talks: bool) \
        -> typ.List[SearchResult]:
    results = []

    for ns, title, date, snapshot, message_id in _perform_search(query, current_user, namespaces, ignore_talks):
        results.append(SearchResult(
            namespace_id=ns,
            title=title,
            date=date,
            snapshot=snapshot,
            message_id=message_id
        ))

    return results


def _perform_search(query: str, current_user: models.User, namespaces: typ.Iterable[int], ignore_talks: bool) \
        -> typ.List[typ.Tuple[int, str, datetime.datetime, str, typ.Optional[int]]]:
    ns_id, title = titles.extract_namespace_and_title(query, ns_as_id=True)
    if ns_id:
        ns_list = [ns_id]
    else:
        ns_list = namespaces
    results = []

    for page in models.Page.objects.filter(title__icontains=title, namespace_id__in=ns_list):
        ns = page.namespace_id
        title = page.title
        if current_user.can_read_page(ns, title):
            revision = page.latest_revision
            snapshot = revision.content[:200]
            if snapshot != revision.content:
                snapshot += "…"
            results.append((ns, title, revision.date, snapshot, None))

    if not ignore_talks:
        for message in models.Message.objects.filter(content__icontains=query, topic__page__namespace_id__in=ns_list):
            page = message.topic.page
            snapshot = message.content[:200]
            if snapshot != message.content:
                snapshot += "…"
            results.append(
                (page.namespace_id, page.title, message.last_edited_on or message.date, snapshot, message.id))

    return results


def get_random_page(namespaces: typ.Iterable[int] = None) -> typ.Optional[models.Page]:
    result = models.Page.objects.filter(namespace_id__in=namespaces)
    if result.count():
        page = random.choice(result)
        page.lock()
        return page
    return None


def get_page(namespace_id: int, title: str) -> typ.Tuple[models.Page, bool]:
    """
    Returns the page instance for the given namespace ID and title.
    The returned object will be uneditable.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page and a boolean equal to True if the page exists or False otherwise.
    """
    if namespace_id != settings.SPECIAL_NS.id:
        page = _get_page(namespace_id, title)
        exists = page is not None and not page.deleted
        if not exists:
            page = models.Page(namespace_id=namespace_id, title=title)
    else:
        page = models.Page(namespace_id=settings.SPECIAL_NS.id, title=title)
        exists = page_exists(settings.SPECIAL_NS.id, title)
    page.lock()
    return page, exists


def get_redirect(wikicode: str) -> typ.Optional[typ.Tuple[str, typ.Optional[str]]]:
    return parser.WikicodeParser.get_redirect(wikicode)


# endregion
# region Subpages


def get_subpages(namespace_id: int, title: str) -> typ.List[models.Page]:
    ns = settings.NAMESPACES.get(namespace_id)
    if not ns or not ns.allows_subpages:
        return []
    pages = models.Page.objects.filter(namespace_id=namespace_id, title__startswith=title + '/')
    return [p.lock() for p in pages]


def get_suppages(namespace_id: int, title: str) -> typ.List[models.Page]:
    ns = settings.NAMESPACES.get(namespace_id)
    if not ns or not ns.allows_subpages:
        return []

    pages = []
    t = ''
    for e in title.split('/')[:-1]:
        if t:
            t += '/'
        t += e
        pages.append(get_page(namespace_id, t)[0])

    return pages


# endregion
# region Page metadata


_MEDIA_BACKEND = media_backends.get_backend(settings.MEDIA_BACKEND_ID)


def get_file_metadata(file_name: str) -> typ.Optional[media_backends.FileMetadata]:
    return _MEDIA_BACKEND.get_file_info(file_name)


def get_page_content_type(content_model: str) -> str:
    return {
        settings.PAGE_TYPE_WIKI: 'text/plain',
        settings.PAGE_TYPE_STYLESHEET: 'text/css',
        settings.PAGE_TYPE_JAVASCRIPT: 'application/javascript',
    }.get(content_model, 'text/plain')


def get_default_content_model(namespace_id: int, title: str):
    content_model = settings.PAGE_TYPE_WIKI
    allow_js_css = (namespace_id in [settings.WIKIPY_NS.id, settings.GADGET_NS.id] or
                    namespace_id == settings.USER_NS.id and '/' in title)
    if allow_js_css and title.endswith('.css'):
        content_model = settings.PAGE_TYPE_STYLESHEET
    elif allow_js_css and title.endswith('.js'):
        content_model = settings.PAGE_TYPE_JAVASCRIPT
    elif namespace_id == settings.MODULE_NS.id:
        content_model = settings.PAGE_TYPE_MODULE
    return content_model


# endregion
# region Revisions


def get_diff(revision_id1: int, revision_id2: int, current_user: models.User, escape_html: bool, keep_lines: int) \
        -> typ.Tuple[_diff.DiffType, models.PageRevision, models.PageRevision, int]:
    try:
        revision1 = models.PageRevision.objects.get(id=revision_id1)
    except models.PageRevision.DoesNotExist:
        raise errors.RevisionDoesNotExist(revision_id1)
    try:
        revision2 = models.PageRevision.objects.get(id=revision_id2)
    except models.PageRevision.DoesNotExist:
        raise errors.RevisionDoesNotExist(revision_id2)

    page1 = revision1.page
    page2 = revision2.page

    if not current_user.can_read_page(page1.namespace_id, page1.title):
        raise errors.PageReadForbidden(page1)
    if not current_user.can_read_page(page2.namespace_id, page2.title):
        raise errors.PageReadForbidden(page2)

    if revision1.page.id == revision2.page.id:
        nb_not_shown = models.PageRevision.objects.filter(page=page1, date__gt=revision1.date,
                                                          date__lt=revision2.date).count()
    else:
        nb_not_shown = 0

    if revision1.content != revision2.content:
        diff = _diff.Diff(revision1, revision2).get(escape_html, keep_lines)
    else:
        diff = []

    revision1.lock()
    revision2.lock()
    return diff, revision1, revision2, nb_not_shown


def get_page_revision(namespace_id: int, title: str, current_user: models.User = None, *, revision_id: int = None) \
        -> typ.Optional[models.PageRevision]:
    """
    Returns a revision for the given page. If revision_id is not specified, the latest non-hidden revision is returned.
    May throw an error if the requested revision ID does not exist for the page or if it is hidden and the user is not
    allowed to see it.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param current_user: The user requesting the revision. Should ALWAYS be specified.
    :param revision_id: The optional revision ID.
    :return: The revision or None if the page does not exist or the user is not allowed to read it.
    """
    if page_exists(namespace_id, title) and (not current_user or current_user.can_read_page(namespace_id, title)):
        page = models.Page.objects.get(namespace_id=namespace_id, title=title)
        if revision_id is not None:
            revision = page.get_revision(revision_id)
        else:
            revision = page.latest_revision

        if not revision or (
                revision.hidden and (not current_user or not current_user.has_right(settings.RIGHT_HIDE_REVISIONS))):
            raise errors.RevisionDoesNotExist(revision_id)

        revision.lock()
        if current_user and not current_user.has_right(settings.RIGHT_HIDE_REVISIONS):
            if revision.author_hidden:
                revision.author = None
            if revision.comment_hidden:
                revision.comment = None

        return revision
    else:
        return None


def get_page_revisions(page: models.Page, current_user: models.User) -> typ.List[models.PageRevision]:
    """
    Returns all revisions for the given page that the given user is allowed to see.

    :param page: The page.
    :param current_user: The current user.
    :return: The revisions.
    """
    if page_exists(page.namespace_id, page.title) and current_user.can_read_page(page.namespace_id, page.title):
        args = {
            'page': page,
        }
        if not current_user.has_right(settings.RIGHT_HIDE_REVISIONS):
            args['hidden'] = False

        res = []
        for r in models.PageRevision.objects.filter(**args).order_by('-date'):
            r.lock()
            if not current_user.has_right(settings.RIGHT_HIDE_REVISIONS):
                if r.author_hidden:
                    r.author = None
                if r.comment_hidden:
                    r.comment = None
            res.append(r)

        return res
    return []


# endregion
# region Categories


def get_page_categories(page: models.Page, get_maintenance: bool) \
        -> typ.List[typ.Tuple[models.Page, models.CategoryData]]:
    categories = []

    for c_name in page.get_categories():
        category_page, _ = get_page(settings.CATEGORY_NS.id, c_name)
        try:
            category_data = models.CategoryData.objects.get(page=category_page)
        except models.CategoryData.DoesNotExist:
            category_data = models.CategoryData(
                page=category_page
            )
            category_data.lock()
            categories.append((category_page, category_data))
        else:
            if get_maintenance or not category_data.maintenance:
                category_data.lock()
                categories.append((category_page, category_data))

    return categories


def get_category_metadata(category_title: str) -> typ.Optional[models.CategoryData]:
    page, exists = get_page(settings.CATEGORY_NS.id, category_title)
    if exists and page.is_category:
        try:
            return models.CategoryData.objects.get(page__title=category_title).lock()
        except models.CategoryData.DoesNotExist:
            return None
    return None


def get_pages_in_category(category_title: str) -> typ.Sequence[typ.Tuple[models.Page, str]]:
    pages = []
    namespaces = [ns_id for ns_id in settings.NAMESPACES if ns_id != settings.CATEGORY_NS.id]

    for page_category in sorted(models.PageCategory.objects.filter(category_name=category_title,
                                                                   page__namespace_id__in=namespaces),
                                key=lambda pc: pc.sort_key or pc.page.title):
        page = page_category.page
        page.lock()
        pages.append((page, page_category.sort_key or page.title))

    return pages


def get_subcategories(category_title: str) -> typ.Sequence[typ.Tuple[models.Page, str]]:
    pages = []

    for page_category in sorted(models.PageCategory.objects.filter(category_name=category_title,
                                                                   page__namespace_id=settings.CATEGORY_NS.id),
                                key=lambda pc: pc.sort_key or pc.page.title):
        page = page_category.page
        page.lock()
        pages.append((page, page_category.sort_key or page.title))

    return pages


# endregion
# region Page operations


def render_wikicode(wikicode: str, context, no_redirect: bool = False, enable_comment: bool = False) \
        -> typ.Union[str, typ.Tuple[str, bool]]:
    """
    Renders the given parsed wikicode.
    :param wikicode: The wikicode to render.
    :param context: The context to use for the render.
    :type context: WikiPy.page_context.PageContext
    :param no_redirect: If true and the wikicode is a redirection,
                        it will be rendered instead of rendering the page it points to.
    :param enable_comment: If true, the generation comment will be appended to the rendered HTML.
    :return: The wikicode rendered as HTML. If no_redirect is true, a boolean will also be returned, indicating whether
             the code is a redirection or not.
    """
    p = parser.WikicodeParser()
    parsed_wikicode = p.parse_wikicode(wikicode, context, no_redirect=no_redirect)
    render = context.skin.render_wikicode(parsed_wikicode, context, enable_comment=enable_comment)

    if no_redirect:
        return render, isinstance(parsed_wikicode, parser.RedirectNode)
    return render


# TODO handle conflicts
@dj_db_trans.atomic
def submit_page_content(context, namespace_id: int, title: str, current_user: models.User, wikicode: str,
                        comment: typ.Optional[str], minor: bool, section_id: int = None,
                        maintenance_category: bool = False):
    exists = page_exists(namespace_id, title)
    if exists:
        page = _get_page(namespace_id, title)
    else:
        page = models.Page(
            namespace_id=namespace_id,
            title=title,
            content_model=get_default_content_model(namespace_id, title)
        )

    if not users.can_edit_page(current_user, namespace_id, title):
        raise errors.PageEditForbidden(page)

    if not exists:
        page.save()
        if namespace_id == settings.CATEGORY_NS.id:
            models.CategoryData(
                page=page,
                maintenance=maintenance_category
            ).save()
    elif namespace_id == settings.CATEGORY_NS.id:
        cd = models.CategoryData.objects.get(page=page)
        cd.maintenance = maintenance_category
        cd.save()

    def _set_page_categories(categories: typ.Dict[str, str]):
        # Add/update categories
        for category_name, sort_key in categories.items():
            pc, created = models.PageCategory.objects.get_or_create(
                page=page,
                category_name=category_name,
                defaults={
                    'sort_key': sort_key,
                }
            )
            if not created:
                pc.sort_key = sort_key
            pc.save()
        # Delete all categories that were removed
        for pc in models.PageCategory.objects.filter(page=page):
            if pc.category_name not in categories:
                pc.delete()

    def _edit_size(old_text: str, new_text: str) -> int:
        return len(new_text.encode('UTF-8')) - len(old_text.encode('UTF-8'))

    latest_revision = page.latest_revision
    prev_content = latest_revision.content if latest_revision else ''

    wikicode = wikicode.replace('\r\n', '\n')
    if section_id is not None:
        header, sections = parser.WikicodeParser.split_sections(prev_content)
        sections[section_id] = wikicode
        new_content = parser.WikicodeParser.paste_sections(header, sections)
    else:
        new_content = wikicode

    parser_ = parser.WikicodeParser()
    parser_.parse_wikicode(wikicode, context, no_redirect=True)
    # TODO categorize errors
    # cf. https://en.wikipedia.org/wiki/Category:Pages_where_template_include_size_is_exceeded
    too_many_transclusions = parser_.max_depth_reached
    too_many_redirects = parser_.too_many_redirects
    circular_transclusion = parser_.circular_transclusion_detected
    called_missing_template = parser_.called_non_existant_template
    _set_page_categories(parser_.categories)

    if not latest_revision or prev_content != new_content:
        size = _edit_size(prev_content, wikicode)
        revision = models.PageRevision(page=page, author=current_user.django_user, content=wikicode, comment=comment,
                                       minor=minor, diff_size=size)
        revision.save()
        if not latest_revision:
            logs.add_log_entry(models.LOG_PAGE_CREATION, current_user, page_namespace_id=page.namespace_id,
                               page_title=page.title, reason=comment)


@dj_db_trans.atomic
def rename_page(context, old_namespace_id: int, old_title: str, new_namespace_id: int, new_title: str,
                reason: str, create_redirection: bool):
    current_user = context.user
    current_page, _ = get_page(old_namespace_id, old_title)
    new_page, _ = get_page(new_namespace_id, new_title)

    if titles.get_full_page_title(current_page.namespace_id, current_page.title) \
            == titles.get_full_page_title(new_page.namespace_id, new_page.title):
        raise errors.PageRenameForbidden(current_page, 'same origin and target titles')
    if not current_page.exists:
        raise errors.PageRenameForbidden(current_page, 'origin page does not exist')
    if new_page.exists:
        raise errors.PageRenameForbidden(current_page, 'target page already exists')
    if not current_user.can_rename_page(current_page.namespace_id, current_page.title):
        raise errors.PageRenameForbidden(current_page, 'rename forbidden')
    if not current_user.can_edit_page(new_page.namespace_id, new_page.title):
        raise errors.PageRenameForbidden(current_page, 'target edit forbidden')

    # TODO move talk page
    # Copy page revisions
    for revision in get_page_revisions(current_page, current_user):
        # Set id to None then save to clone model instance
        revision.id = None
        revision.page = new_page
        revision.save()

    # Create redirection if necessary
    if create_redirection or not current_user.has_right(settings.RIGHT_DELETE_PAGES):
        wikicode = f'@REDIRECT[[{new_page.full_title}]]'
        comment = reason
        submit_page_content(context, current_page.namespace_id, current_page.title, current_user, wikicode, comment)
    else:
        # TODO delete the old page
        pass

    logs.add_log_entry(
        models.LOG_PAGE_RENAME,
        performer=current_user,
        page_namespace_id=current_page.namespace_id,
        page_title=current_page.title,
        new_page_namespace_id=new_page.namespace_id,
        new_page_title=new_page.title,
        reason=reason,
        created_redirection=create_redirection
    )


@dj_db_trans.atomic
def protect_page(namespace_id: int, title: str, current_user: models.User, protection_level: str, reason: str,
                 apply_to_subpages: bool, expiration_date: datetime.datetime):
    current_page, _ = get_page(namespace_id, title)

    if not current_user.has_right(settings.RIGHT_PROTECT_PAGES) or namespace_id == settings.SPECIAL_NS.id:
        raise errors.PageProtectionForbidden(current_page)

    pages = [current_page]
    if apply_to_subpages:
        pages.extend(get_subpages(namespace_id, title))

    for page in pages:
        try:
            prev_protection = models.PageProtectionStatus.objects.get(
                page_namespace_id=page.namespace_id,
                page_title=page.title
            )
        except models.PageProtectionStatus.DoesNotExist:
            pass  # No previous protections for the page, skip
        else:
            prev_protection.delete()

        if protection_level != settings.GROUP_ALL:
            # No entry = no protection
            models.PageProtectionStatus(
                page_namespace_id=page.namespace_id,
                page_title=page.title,
                protection_level=protection_level,
                reason=reason,
                expiration_date=expiration_date
            ).save()
        logs.add_log_entry(
            models.LOG_PAGE_PROTECTION,
            performer=current_user,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            protection_level=protection_level,
            reason=reason,
            expiration_date=expiration_date
        )


def get_page_protection(namespace_id: int, title: str) \
        -> typ.Optional[typ.Tuple[models.PageProtectionStatus, models.PageProtectionLogEntry]]:
    try:
        pp = models.PageProtectionStatus.objects.get(page_namespace_id=namespace_id, page_title=title)
    except models.PageProtectionStatus.DoesNotExist:
        return None
    ppj = models.PageProtectionLogEntry.objects.filter(page_namespace_id=namespace_id, page_title=title).latest(
        'date')

    return pp.lock(), ppj.lock()


# endregion
# region Talks


def get_messages_for_page(namespace_id: int, title: str, current_user: models.User = None,
                          ignore_hidden_topics: bool = True) -> typ.Dict[models.TalkTopic, typ.List[models.Message]]:
    return {}  # TODO


def create_topic(current_user: models.User, title: str):
    pass  # TODO


def submit_message(current_user: models.User, content: str, topic_id: int = None, reply_to: int = None):
    pass  # TODO


def edit_message(current_user: models.User, content: str, message_id: int):
    pass  # TODO


def delete_topic(current_user: models.User, topic_id: int):
    pass  # TODO


def restore_topic(current_user: models.User, topic_id: int):
    pass  # TODO


def delete_message(current_user: models.User, message_id: int):
    pass  # TODO


def restore_message(current_user: models.User, message_id: int):
    pass  # TODO


# endregion
# region Utility


def get_page_content(ns_id: int, title: str) -> typ.Optional[str]:
    revision = get_page_revision(ns_id, title)
    if revision:
        return revision.content
    return None


def get_message(notice_name: str) -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
    if revision:
        return revision.content, revision.page.content_language
    return '', None


def get_page_message(page: models.Page, notice_name: str, no_per_title_notice: bool = False) \
        -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    if page.namespace_id != settings.SPECIAL_NS.id:
        message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
        ns_message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}-{page.namespace_id}')
        if not no_per_title_notice:
            page_message_revision = get_page_revision(settings.WIKIPY_NS.id,
                                                      f'Message-{notice_name}-{page.namespace_id}-{page.title}')
        else:
            page_message_revision = None

        if page_message_revision:
            return page_message_revision.content, page_message_revision.page.content_language
        elif ns_message_revision:
            return ns_message_revision.content, ns_message_revision.page.content_language
        elif message_revision:
            return message_revision.content, message_revision.page.content_language
    return '', None


def _get_page(namespace_id: int, title: str) -> typ.Optional[models.Page]:
    """
    Returns the page instance for the given namespace ID and title.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page or None if it doesn’t exist.
    """
    try:
        return models.Page.objects.get(namespace_id=namespace_id, title=title)
    except models.Page.DoesNotExist:
        return None

# endregion
