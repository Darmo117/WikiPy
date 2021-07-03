"""
This module defines functions to interact with pages.
"""
import dataclasses
import datetime
import random
import typing as typ

import django.core.paginator as dj_page
import django.db.transaction as dj_db_trans

from . import _diff, errors, titles, logs, users
from .. import settings, models, special_pages, parser, media_backends, util

page_title_validator = models.page_title_validator


# region Get pages


def page_exists(namespace_id: int, title: str, talk: bool = False) -> bool:
    """
    Checks whether a page or its talk page exists. Works for both special and normal pages.
    Performs DB operations.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param talk: True to check the talk page.
    :return: True if the page exists, false otherwise.
    """
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


def paginate(current_user: models.User, values: typ.Iterable[typ.Any], url_params: typ.Dict[str, str]) \
        -> typ.Tuple[dj_page.Paginator, int]:
    """
    Paginates the given list of values.

    :param current_user: The current user. Used to get the default revisions list size.
    :param values: Values to paginate.
    :param url_params: Current page’s URL parameters.
    :return: A Paginator object and an int corresponding to the current page.
    """
    page = max(1, util.get_param(url_params, 'page', expected_type=int, default=1))
    number_per_page = min(settings.REVISIONS_LIST_PAGE_MAX,
                          max(settings.REVISIONS_LIST_PAGE_MIN,
                              util.get_param(url_params, 'limit', expected_type=int,
                                             default=current_user.data.default_revisions_list_size)))

    return dj_page.Paginator(values, number_per_page), page


@dataclasses.dataclass(frozen=True)
class SearchResult:
    """A simple object to wrap search results."""
    namespace_id: int
    title: str
    date: datetime.datetime
    message_id: typ.Optional[int]
    snapshot: str


def search(query: str, current_user: models.User, namespaces: typ.Iterable[int], ignore_talks: bool) \
        -> typ.List[SearchResult]:
    """
    Searches for pages that match the given query.

    :param query: The raw query string.
    :param current_user: The user that performed the search operation.
    :param namespaces: Namespace IDs to search in.
    :param ignore_talks: If true, talk pages will be ignored.
    :return: A list of SearchResult objects that match the query.
    """
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
    """
    Actual implementation of the search operation.

    :param query: The raw query string.
    :param current_user: The user that performed the search operation.
    :param namespaces: Namespace IDs to search in.
    :param ignore_talks: If true, talk pages will be ignored.
    :return: A list of tuple objects that match the query:
             (page’s namespace ID, page’s title, last edit date, snapshot text, [message ID]).
    """
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
    """
    Returns a random page among all pages in the given namespaces (except special pages).

    :param namespaces: Namespace IDs to pick a page into.
    :return: A random page or None if none were found in the given namespaces.
    """
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
    """
    If the given wikicode is a redirection, returns the full page title and the anchor.

    :param wikicode: The wikicode.
    :return: The full page title and anchor if the wikicode is a redirection; None otherwise.
    """
    return parser.WikicodeParser.get_redirect(wikicode)


# endregion
# region Subpages


def get_subpages(namespace_id: int, title: str) -> typ.List[models.Page]:
    """
    Returns all subpages of the given page.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The list of subpages.
    """
    ns = settings.NAMESPACES.get(namespace_id)
    if not ns or not ns.allows_subpages:
        return []
    pages = models.Page.objects.filter(namespace_id=namespace_id, title__startswith=title + '/')
    return [p.lock() for p in pages]


def get_suppages(namespace_id: int, title: str, ignore_non_existant: bool = False) -> typ.List[models.Page]:
    """
    Returns all parent pages of the given page.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param ignore_non_existant: If true, the list will not contain parent pages that do not exist.
    :return: The list of parent pages.
    """
    ns = settings.NAMESPACES.get(namespace_id)
    if not ns or not ns.allows_subpages:
        return []

    pages = []
    t = ''
    for e in title.split('/')[:-1]:
        if t:
            t += '/'
        t += e
        page, exists = get_page(namespace_id, t)
        if exists:
            pages.append(page)

    return pages


# endregion
# region Page metadata


_MEDIA_BACKEND = media_backends.get_backend(settings.MEDIA_BACKEND_ID)


def get_file_metadata(file_name: str) -> typ.Optional[media_backends.FileMetadata]:
    """
    Gets metadata for the given file. Uses the defined media backend.

    :param file_name: File’s name.
    :return: The file’s metadata or None if none were found or the file does not exist.
    """
    return _MEDIA_BACKEND.get_file_info(file_name)


def get_page_content_type(content_model: str) -> str:
    """
    Returns the content type for the given page content model.

    :param content_model: The content model.
    :return: The corresponding content type.
    """
    return {
        settings.PAGE_TYPE_WIKI: 'text/plain',
        settings.PAGE_TYPE_STYLESHEET: 'text/css',
        settings.PAGE_TYPE_JAVASCRIPT: 'application/javascript',
        settings.PAGE_TYPE_MODULE: 'text/x-python',
    }.get(content_model, 'text/plain')


def get_default_content_model(namespace_id: int, title: str):
    """
    Returns the default content model for the given page title.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: Page’s default content model.
    """
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
    """
    Computes the difference between two page revisions.
    See WikiPy.api.Diff for more details.

    :param revision_id1: First revision ID.
    :param revision_id2: Second revision ID.
    :param current_user: Current user.
    :param escape_html: If true, HTML tags will be escaped in the result.
    :param keep_lines: If true, all unchanged lines will be kept.
    :return: A tuple containing the actual diff, the two revisions and the number of diffs not shown between these two
             (if the two revisions are from the same page).
    :raises WikiPy.api.errors.RevisionDoesNotExistError: If at least one of the two revision IDs does not exist.
    :raises WikiPy.api.errors.PageReadForbiddenError: If the user is not allowed to read at least one of the two
            revisions.
    """
    try:
        revision1 = models.PageRevision.objects.get(id=revision_id1)
    except models.PageRevision.DoesNotExist:
        raise errors.RevisionDoesNotExistError(revision_id1)
    try:
        revision2 = models.PageRevision.objects.get(id=revision_id2)
    except models.PageRevision.DoesNotExist:
        raise errors.RevisionDoesNotExistError(revision_id2)

    page1 = revision1.page
    page2 = revision2.page

    if not current_user.can_read_page(page1.namespace_id, page1.title):
        raise errors.PageReadForbiddenError(page1)
    if not current_user.can_read_page(page2.namespace_id, page2.title):
        raise errors.PageReadForbiddenError(page2)

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
            raise errors.RevisionDoesNotExistError(revision_id)

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


def get_page_categories(namespace_id: int, title: str, get_maintenance: bool) \
        -> typ.List[typ.Tuple[models.Page, models.CategoryData]]:
    """
    Returns all the categories the given page belongs to.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param get_maintenance: If true, maintenance categories will be returned too.
    :return: A list of tuples, each containing the category Page object and the associated CategoryData.
    """
    categories = []

    for c_name in get_page(namespace_id, title)[0].get_categories():
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
    """
    Returns the metadata for the given category.

    :param category_title: Category’s title.
    :return: A CategoryData object or None if the category does not exist or the page is not a category.
    """
    page, exists = get_page(settings.CATEGORY_NS.id, category_title)
    if exists and page.is_category:
        try:
            return models.CategoryData.objects.get(page__title=category_title).lock()
        except models.CategoryData.DoesNotExist:
            return None
    return None


def get_pages_in_category(category_title: str) -> typ.Sequence[typ.Tuple[models.Page, str]]:
    """
    Returns all pages in the given category.

    :param category_title: Category’s title.
    :return: The list of pages ordered by sort key/title.
    """
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
    """
    Returns all categories in the given category.

    :param category_title: Category’s title.
    :return: A list of tuples, each containing the Page object with its sort key/title.
    """
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
def submit_page_content(context, namespace_id: int, title: str,
                        wikicode: str, comment: typ.Optional[str], minor: bool, section_id: int = None,
                        maintenance_category: bool = False, current_revision_id: int = None):
    """
    Submits new content for the given page.

    :param context: Current page context.
    :type context: WikiPy.page_context.PageContext
    :param namespace_id: Namespace ID of the page to submit to.
    :param title: Title of the page to submit to.
    :param wikicode: The new wikicode.
    :param comment: The revision comment.
    :param minor: True to mark the revision as minor.
    :param section_id: The ID of the section that was edited. If specified, only this section will be edited.
    :param maintenance_category: If true and the page is a category, marks it as a maintenance category.
    :param current_revision_id: ID of the revision this edit was made from, should be None if this is the first edit.
    :raises PageEditForbiddenError: If the user is not allowed to edit the page.
    :raises PageEditConflictError: If another user already edited the same page or section from the same revision.
    """
    exists = page_exists(namespace_id, title)
    if exists:
        if current_revision_id is None:
            raise ValueError('current_revision should only be None when creating a page')
        page = _get_page(namespace_id, title)
    else:
        page = models.Page(
            namespace_id=namespace_id,
            title=title,
            content_model=get_default_content_model(namespace_id, title)
        )

    if not context.user.can_edit_page(namespace_id, title)[0]:
        raise errors.PageEditForbiddenError(page)

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
        revision = models.PageRevision(page=page, author=context.user.django_user, content=wikicode, comment=comment,
                                       minor=minor, diff_size=size)
        revision.save()
        if not latest_revision:
            logs.add_log_entry(models.LOG_PAGE_CREATION, context.user, page_namespace_id=page.namespace_id,
                               page_title=page.title, reason=comment)


# TODO abstraire le concept d’action sous forme de classes ?
@dj_db_trans.atomic
def rename_page(context, old_namespace_id: int, old_title: str, new_namespace_id: int, new_title: str,
                reason: str, create_redirection: bool, move_talks: bool):
    """
    Renames the given page. Revision history of the old page will be copied to the new page’s.
    Talks will be optionally moved to the new page.

    :param context: Current page context.
    :type context: WikiPy.page_context.PageContext.
    :param old_namespace_id: Namespace ID of the old page.
    :param old_title: Title of the old page.
    :param new_namespace_id: New Namespace ID.
    :param new_title: New title.
    :param reason: Reason for renaming.
    :param create_redirection: If true or the user is not allowed to delete pages,
    a redirection from the old to the new page will be created.
    :param move_talks: If true, all talks will be moved to the new page.
    :raises PageRenameForbiddenError: If one of the following situations occured:
    - the user is not allowed to rename pages
    - both the old and new page have the same title
    - the old page to rename does not exist
    - the new page already exists
    - the user is not allowed to edit the new page
    """
    current_user = context.user
    current_page, _ = get_page(old_namespace_id, old_title)
    new_page, _ = get_page(new_namespace_id, new_title)

    if titles.get_full_page_title(current_page.namespace_id, current_page.title) \
            == titles.get_full_page_title(new_page.namespace_id, new_page.title):
        raise errors.PageRenameForbiddenError(current_page, 'same origin and target titles')
    if not current_page.exists:
        raise errors.PageRenameForbiddenError(current_page, 'origin page does not exist')
    if new_page.exists:
        raise errors.PageRenameForbiddenError(current_page, 'target page already exists')
    if not current_user.can_rename_page(current_page.namespace_id, current_page.title):
        raise errors.PageRenameForbiddenError(current_page, 'rename forbidden')
    if not current_user.can_edit_page(new_page.namespace_id, new_page.title)[0]:
        raise errors.PageRenameForbiddenError(current_page, 'target edit forbidden')

    # Copy page revisions
    for revision in get_page_revisions(current_page, current_user):
        # Set id to None then save to clone model instance
        revision.id = None
        revision.page = new_page
        revision.save()

    if move_talks:
        # TODO move talk page
        pass

    # Create redirection if necessary
    if create_redirection or not current_user.has_right(settings.RIGHT_DELETE_PAGES):
        wikicode = f'@REDIRECT[[{new_page.full_title}]]'
        comment = reason
        current_revision_id = get_page_revision(current_page.namespace_id, current_page.title, current_user)
        submit_page_content(context, current_page.namespace_id, current_page.title, wikicode, comment,
                            current_revision_id=current_revision_id)
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
def protect_page(namespace_id: int, title: str, performer: models.User, protection_level: str, reason: str,
                 apply_to_talk: bool, apply_to_subpages: bool, expiration_date: datetime.datetime):
    """
    Sets the protection level for the given pages. Any previous protection level will be overriden.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param performer: The user performing this action.
    :param protection_level: New protection level.
    :param reason: Reason for protecting.
    :param apply_to_talk: If true, the protection level will apply to talks as well.
    :param apply_to_subpages: If true, the protection level will be applied to all
    subpages *at the time* this action is performed.
    :param expiration_date: The date at which the protection level will revert to the default one.
     Keep empty for infinite protection.
    :raises PageProtectionForbiddenError: If the user is not allowed to set page protection level
    or the page is a special page.
    """
    current_page, _ = get_page(namespace_id, title)

    if not performer.has_right(settings.RIGHT_PROTECT_PAGES) or namespace_id == settings.SPECIAL_NS.id:
        raise errors.PageProtectionForbiddenError(current_page)

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
                applies_to_talk_page=apply_to_talk,
                reason=reason,
                expiration_date=expiration_date
            ).save()
        logs.add_log_entry(
            models.LOG_PAGE_PROTECTION,
            performer=performer,
            page_namespace_id=page.namespace_id,
            page_title=page.title,
            protection_level=protection_level,
            reason=reason,
            expiration_date=expiration_date,
            applies_to_talk_page=apply_to_talk
        )


def get_page_protection(namespace_id: int, title: str) \
        -> typ.Optional[typ.Tuple[models.PageProtectionStatus, models.PageProtectionLogEntry]]:
    """
    Returns the protection status and log for the given page.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: A tuple containing the protection status and log, or None if the page is not protected.
    """
    try:
        pp = models.PageProtectionStatus.objects.get(page_namespace_id=namespace_id, page_title=title)
    except models.PageProtectionStatus.DoesNotExist:
        return None
    ppj = models.PageProtectionLogEntry.objects.filter(page_namespace_id=namespace_id, page_title=title).latest('date')

    return pp.lock(), ppj.lock()


# endregion
# region Talks

MessageList = typ.Dict[models.TalkTopic, typ.List[typ.Union[models.Message, 'MessageList']]]


def get_messages_for_page(namespace_id: int, title: str, current_user: models.User = None,
                          ignore_hidden_topics: bool = True) -> MessageList:
    return {}  # TODO


def create_topic(performer: models.User, title: str, parent_topic_id: int, page_namespace_id: int, page_title: str):
    if not performer.can_edit_page(page_namespace_id, page_title)[1]:
        raise errors.PageEditForbiddenError(get_page(page_namespace_id, page_title))

    models.TalkTopic(
        author=performer.django_user,
        page_namespace_id=page_namespace_id,
        page_title=page_title,
        parent_topic=models.TalkTopic.objects.get(id=parent_topic_id),
    ).save()
    models.TalkTopicRevision(
        content=title
    ).save()


def pin_topic(performer: models.User, topic_id: int, pin: bool):
    users.check_rights(performer, settings.RIGHT_PIN_TOPICS)
    topic = models.TalkTopic.objects.get(id=topic_id)
    topic.pinned = pin
    topic.save()


def submit_message(performer: models.User, content: str, comment: str = None, minor_edit: bool = False,
                   topic_id: int = None, reply_to: int = None):
    pass  # TODO


def edit_message(performer: models.User, message_id: int, content: str, comment: str = None,
                 minor_edit: bool = False):
    pass  # TODO


def delete_topic(performer: models.User, topic_id: int):
    pass  # TODO


def restore_topic(performer: models.User, topic_id: int):
    pass  # TODO


def delete_message(performer: models.User, message_id: int):
    pass  # TODO


def restore_message(performer: models.User, message_id: int):
    pass  # TODO


# endregion
# region Utility


def get_page_content(ns_id: int, title: str) -> typ.Optional[str]:
    """
    Returns the content of the last non-deleted revision of the given page.

    :param ns_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page’s content or None if the page does not exits.
    """
    revision = get_page_revision(ns_id, title)
    if revision:
        return revision.content
    return None


def get_message(notice_name: str) -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    """
    Returns the message with the given name.
    Returned message will be fetched from the page named WikiPy:Message-<notice_name>.

    :param notice_name: Name of the message.
    :return: The message and its language, or an empty string and None if the message page does not exist.
    """
    revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
    if revision:
        return revision.content, revision.page.content_language
    return '', None


def get_page_message(namespace_id: int, title: str, notice_name: str, no_per_title_notice: bool = False) \
        -> typ.Tuple[str, typ.Optional[settings.i18n.Language]]:
    """
    Returns the message with the given name for the given page.
    Returned message will be fetched from the following pages (in that order):
        - WikiPy:Message-<notice_name>-<namespace_id>-<title> (if enabled)
        - WikiPy:Message-<notice_name>-<namespace_id>
        - WikiPy:Message-<notice_name>

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :param notice_name: Name of the message.
    :param no_per_title_notice: If true, the function will not try to fetch the page-specific message.
    :return: The message and its language, or an empty string and None if the message page does not exist.
    """
    if namespace_id != settings.SPECIAL_NS.id:
        message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}')
        ns_message_revision = get_page_revision(settings.WIKIPY_NS.id, f'Message-{notice_name}-{namespace_id}')
        if not no_per_title_notice:
            # TODO fetch page *beginning* with the title
            page_message_revision = get_page_revision(settings.WIKIPY_NS.id,
                                                      f'Message-{notice_name}-{namespace_id}-{title}')
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
    The page object will NOT be locked.

    :param namespace_id: Page’s namespace ID.
    :param title: Page’s title.
    :return: The page or None if it doesn’t exist.
    """
    try:
        return models.Page.objects.get(namespace_id=namespace_id, title=title)
    except models.Page.DoesNotExist:
        return None

# endregion
