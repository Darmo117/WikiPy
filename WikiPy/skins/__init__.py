"""This module defines classes and functions related to skins.
Skins are used to render the pages to users.

All skins have to be installed in this package.
Skin subclasses must be defined in a separate sub-package and define a load_skin() function
that takes in the skins directory path as a string and returns an instance of the skin’s class.

Skins license files should be inside the skin’s directory and named “LICENSE”.
The directory should also contain a skin.json file that must feature the following attributes:
    - version (string): the skin’s version.
    - build_date (string): the skin’s build date as an ISO date (YYYY-MM-DDTHH:mm:SS).
    - home_url (string): the URL to the page that describes the skin. May be null.
    - license (string): the skin’s license. May be null.
    - fallback_language (string): the code of the language to use
        if there are no mapping for a translation key in a given language.
    - authors (array): the list of people that worked on the skin. Each item should have the following attributes:
        - name: the person’s full name or alias.
        - url: the person’s home page URL. May be null.

Skins’ packages should have the following structure:
    - langs: a directory that contains language files. Each language file should be named “<language code>.json”.
        Each language file should have these two attributes:
            - name (string): the skin’s name in the language.
            - description (string): the skin’s description in the language.
    - skin.json: the file described above.
    - __init__.py: the file that defines the load_skin function returning the skin’s class.
    - LICENSE (optional): the file containing the full license.
"""
import abc
import dataclasses
import importlib
import json
import logging
import os
import time
import typing as typ
import urllib.parse

import django.utils.safestring as dj_safe
from django.conf import settings as dj_settings

from .. import apps, settings, special_pages, page_context
from ..api import titles as api_titles, pages as api_pages


@dataclasses.dataclass(frozen=True)
class MenuItem:
    """A simple class that represents a menu item."""
    item_id: str = None
    access_key: str = None
    icon: str = None
    add_page_title: bool = False
    add_base_page_title: bool = False
    add_user_name: bool = False
    add_return_to: bool = False
    requires_page_exists: bool = False
    requires_user_page: bool = False
    requires_not_special_page: bool = False
    requires_logged_in: bool = False
    requires_logged_out: bool = False
    requires_user_can_read: bool = False
    disable_access_key: bool = False
    is_special: bool = False
    url: str = None
    text: str = None


class PageTemplate:
    """The page template object provides the list of menus and their items that every skin should display.

    The page template is located in the “page_template.json” file within this package.
    """

    def __init__(self):
        self.__menus_links = {}

        with open(os.path.join(dj_settings.BASE_DIR, apps.WikiPyConfig.name, 'skins', 'page_template.json'),
                  mode='r', encoding='UTF-8') as f:
            json_obj = json.load(f)

            for menu_id, menu_items in json_obj['menus'].items():
                self.__menus_links[menu_id] = []
                for item in menu_items:
                    args = {
                        'item_id': None,
                        'is_special': False,
                        'access_key': None,
                        'icon': None,
                        'add_page_title': bool(item.get('add_page_title', False)),
                        'add_base_page_title': bool(item.get('add_base_page_title', False)),
                        'add_user_name': bool(item.get('add_user_name', False)),
                        'add_return_to': bool(item.get('add_return_to', False)),
                        'requires_page_exists': bool(item.get('requires_page_exists', False)),
                        'requires_not_special_page': bool(item.get('requires_not_special_page', False)),
                        'requires_user_page': bool(item.get('requires_user_page', False)),
                        'requires_logged_in': bool(item.get('requires_logged_in', False)),
                        'requires_logged_out': bool(item.get('requires_logged_out', False)),
                        'requires_user_can_read': bool(item.get('requires_user_can_read', False)),
                        'disable_access_key': bool(item.get('disable_access_key', False)),
                    }

                    if 'special_page_id' in item:
                        args['item_id'] = item['special_page_id']
                        args['is_special'] = True
                    else:
                        args['item_id'] = item['item_id']
                        args['icon'] = item.get('icon')
                        args['access_key'] = item.get('access_key')
                    self.__menus_links[menu_id].append(MenuItem(**args))

    def get_menu_items(self, menu_id: str, context) -> typ.List[MenuItem]:
        """
        Returns the items for a specific menu ID.
        Items will be filtered using the given page context.

        :param menu_id: ID of the menu to return the items of.
        :param context: Context of the page being rendered.
        :type context: WikiPy.page_context.PageContext
        :return: The list of items for the given menu ID.
        """

        def f(item: MenuItem) -> bool:
            return (  # Check if the current page exists if required
                    (not item.requires_page_exists or context.page_exists)
                    # Check if the current page is not a special page if required
                    and (not item.requires_not_special_page or context.page.namespace.id != settings.SPECIAL_NS.id)
                    # Check if the current page is not a user page if required
                    and (not item.requires_user_page or context.page.namespace.id == settings.USER_NS.id)
                    # Check if the user is logged in if required
                    and (not item.requires_logged_in or context.user.is_logged_in)
                    # Check if the user is logged out if required
                    and (not item.requires_logged_out or not context.user.is_logged_in)
                    # Check if the user can read the page
                    and (not item.requires_user_can_read or context.user_can_read)
                    # Check if the current page is special and the user has all rights required for this special page
                    and (not item.is_special
                         or all([context.user.has_right(r)
                                 for r in special_pages.get_special_page_for_id(item.item_id).requires_rights])))

        return list(filter(f, self.__menus_links.get(menu_id, [])))


_PAGE_TEMPLATE = PageTemplate()


class Skin(settings.resource_loader.ExternalResource, abc.ABC):
    def __init__(self, path: str, ident: str, **body_attrs: str):
        """This object defines a skin.

        :param path: The skins’ directory path.
        :param ident: The skins’s ID.
        :param body_attrs: A dictionary containing attributes to add to the body tag on each page.
        """
        super().__init__(path, 'skin', ident)
        self.__body_attrs = dict(body_attrs)

    @property
    def body_attrs(self) -> str:
        """The string of attributes to add to the body tag."""
        return dj_safe.mark_safe(' '.join(map(lambda e: f'{e[0]}="{e[1]}"', self.__body_attrs.items())))

    @property
    def additional_menus(self) -> typ.List[str]:
        """Returns a list of menus defined in the WikiPy:SideMenus pages, but not present in the page template."""
        side_menus = api_pages.get_page_content(settings.WIKIPY_NS.id, 'SideMenus', performer=None)
        items = []
        if side_menus:
            for line in side_menus.split('\n'):
                if line.startswith('*') and not line.startswith('**'):
                    name = line[1:].strip()
                    if name != 'navigation':
                        items.append(name)
        return items

    def get_rendered_menu_items(self, menu_id: str, context, *link_classes: str) -> typ.List[str]:
        """Returns the items for a specific menu ID.
        Items to actually render will be filtered using the given page context.

        :param menu_id: ID of the menu to return the items of.
        :param context: Context of the page being rendered.
        :type context: WikiPy.page_context.TemplateContext
        :param link_classes: Optional classes to apply to the HTML links.
        :return: The list of items for the given menu ID.
        """
        rendered_items = []
        c: page_context.PageContext = context['wpy_context']

        if menu_id == 'categories' and hasattr(c, 'page_categories'):
            for category_page, category_data in c.page_categories:
                tooltip = c.language.translate('title.maintenance_category.tooltip')
                icon = (f'<span class="mdi mdi-tools" title="{tooltip}"></span> ' if category_data.maintenance else '')
                rendered_items.append(icon + self.format_internal_link(
                    language=c.language,
                    current_page_title=c.page.full_title,
                    page_title=api_titles.get_full_page_title(settings.CATEGORY_NS.id, category_page.title),
                    text=category_page.title,
                    css_classes=link_classes
                ))

        else:
            items = _PAGE_TEMPLATE.get_menu_items(menu_id, c)

            if menu_id == 'navigation' or menu_id in self.additional_menus:
                # TODO optimiser
                side_menus = api_pages.get_page_content(settings.WIKIPY_NS.id, 'SideMenus', performer=c.user)
                default_items = {i.item_id: i for i in items}
                current_menu = None
                items = []

                if side_menus:
                    for line in side_menus.split('\n'):
                        if line.startswith('**') and current_menu == menu_id:
                            line = line[2:].strip()
                            if '|' in line:
                                url, text = line.strip().split('|', maxsplit=1)
                            else:
                                url = line.strip()
                                text = url
                            if url == 'main_page':
                                if text == url:
                                    text = settings.MAIN_PAGE_TITLE
                                url = api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID,
                                                                     settings.MAIN_PAGE_TITLE)
                            if url in default_items:
                                items.append(default_items[url])
                            else:
                                items.append(MenuItem(text=text, url=url))

                        elif line.startswith('*'):
                            current_menu = line[1:].strip()

            for item in items:
                args = {}

                anchor = None

                if isinstance(item, str):
                    rendered_items.append('-' + item)
                else:
                    if item.is_special:
                        page = special_pages.get_special_page_for_id(item.item_id)
                        ns_id = settings.SPECIAL_NS.id
                        title = page.get_title()
                        icon = page.icon
                        access_key = page.access_key
                        text = page.display_title(c.language)
                        tooltip = c.language.translate(f'special.{page.id}.tooltip', none_if_undefined=True) or text

                    elif item.item_id:
                        item_id = item.item_id
                        ns_id = c.page.namespace.id
                        title = c.page.title
                        icon = item.icon
                        access_key = item.access_key
                        text = c.language.translate(f'link.menu.{item_id}.label')
                        tooltip = c.language.translate(f'link.menu.{item_id}.tooltip')

                        if item_id == 'permalink':
                            args['revision_id'] = c.page.latest_revision.id

                        elif item_id == 'read' and context.request.GET.get('revision_id'):
                            args['revision_id'] = context.request.GET['revision_id']

                        elif item_id == 'talk':
                            args['action'] = 'talk'

                        elif item_id == 'edit':
                            args['action'] = 'edit'
                            if context.request.GET.get('revision_id'):
                                args['revision_id'] = context.request.GET['revision_id']
                            if c.user_can_edit:
                                if not c.page_exists:
                                    text = c.language.translate(f'link.menu.create.label')
                                    tooltip = c.language.translate(f'link.menu.create.tooltip')
                            else:
                                text = c.language.translate(f'link.menu.source.label')
                                tooltip = c.language.translate(f'link.menu.source.tooltip')

                        elif item_id == 'history':
                            args['action'] = 'history'

                        elif item_id in ['user_page', 'user_talk']:
                            ns_id = settings.USER_NS.id
                            title = c.user.username
                            if item_id == 'user_talk':
                                args['action'] = 'talk'

                    else:
                        ns_id, title = api_titles.extract_namespace_and_title(item.url, ns_as_id=True)
                        if '#' in title:
                            title, anchor = title.split('#', maxsplit=1)
                        text = item.text
                        tooltip = api_titles.get_full_page_title(ns_id, title)
                        icon = None
                        access_key = None

                    if item.add_page_title:
                        title += '/' + c.page.full_title
                    if item.add_base_page_title:
                        title += '/' + c.page.title.split('/')[0]
                    if item.add_user_name:
                        title += '/' + c.user.username
                    if item.add_return_to:
                        args['return_to'] = context.request.get_full_path()
                        args['is_path'] = 1
                    if icon:
                        text = f'<span class="mdi mdi-{icon}"></span> ' + text

                    rendered_items.append(self.format_internal_link(
                        language=c.language,
                        current_page_title='',
                        page_title=api_titles.get_full_page_title(ns_id, title),
                        anchor=anchor,
                        text=text,
                        tooltip=tooltip,
                        access_key=access_key if not item.disable_access_key else None,
                        css_classes=link_classes,
                        url_params=args
                    ))

        return rendered_items

    def format_internal_link(self, language, current_page_title: str, page_title: str, text: str = None,
                             tooltip: str = None, anchor: str = None, no_red_link: bool = False,
                             css_classes: typ.Sequence[str] = None, access_key: str = None, only_url: bool = False,
                             new_tab: bool = False, id_: str = None, data_attributes: typ.Dict[str, str] = None,
                             url_params: typ.Dict[str, typ.Any] = None) -> str:
        """Renders an internal link.

        :param language: The current page language.
        :param current_page_title: The title of the current page.
        :param page_title: The title of the target page.
        :param text: The text to display instead of the page’s name and anchor.
        :param tooltip: The links tooltip.
        :param anchor: The anchor in the target page.
        :param no_red_link: If true and the target page does not exist, the link will not appear red.
        :param css_classes: CSS classes to add to the link.
        :param access_key: The access key for this link.
        :param only_url: If true, only the URL will be returned, without the rendered tags.
        :param new_tab: If true, the link will open a new tab or window (target="_blank").
        :param id_: The link’s id attribute’s value.
        :param data_attributes: Data attributes to add to the link.
        :param url_params: Parameters to add to the URL.
        :return: The HTML link or the URL.
        """
        url_params = url_params or {}
        ns_id, title = api_titles.extract_namespace_and_title(page_title, ns_as_id=True)
        page_exists = no_red_link or api_pages.page_exists(ns_id, title, talk=url_params.get('action') == 'talk')
        url = api_titles.get_page_url(ns_id, title)
        link_text = text or page_title
        if tooltip is not None:
            link_tooltip = tooltip
        else:
            link_tooltip = page_title

        if current_page_title == page_title and not anchor and len(url_params) == 0:
            return f'<strong class="wpy-self-link">{link_text}</strong>' if not only_url else ''

        elif page_exists or url_params.get('action') == 'talk':
            params = urllib.parse.urlencode(
                url_params,
                # True only if at least one of the params is iterable, else an error would be raised
                doseq=any(map(lambda e: isinstance(e, typ.Iterable), url_params))
            )
            if params:
                url += '?' + params
            if anchor:
                url += '#' + anchor

        elif ns_id != settings.SPECIAL_NS.id:
            url += '?action=edit&redlink=1'
            paren = language.translate('link.redlink.tooltip')
            link_tooltip += f' ({paren})'

        if only_url:
            return url
        return self._format_link(url, link_text, link_tooltip, page_exists, css_classes or [], access_key,
                                 external=new_tab, id_=id_, **(data_attributes or {}))

    def format_external_link(self, url: str, text: str = None, css_classes: typ.Sequence[str] = None) -> str:
        """Renders an external link.

        :param url: The link’s URL.
        :param text: The text to display instead of the URL.
        :param css_classes: CSS classes to add to the link.
        :return: The rendered link.
        """
        return self._format_link(url, text or url, tooltip=url, page_exists=True, css_classes=css_classes or [],
                                 external=True)

    @abc.abstractmethod
    def _format_link(self, url: str, text: str, tooltip: str, page_exists: bool, css_classes: typ.Sequence[str],
                     access_key: str = None, external: bool = False, id_: str = None, **data_attributes) -> str:
        """Renders an HTML link.
        It is called by the format_internal_link and format_external_link
        methods after they have processed some of their parameters.

        :param url: The link’s URL.
        :param text: The text to display instead of the URL.
        :param tooltip: The links tooltip.
        :param page_exists: Whether the target page exists. Always true for external links.
        :param css_classes: CSS classes to add to the link.
        :param access_key: The access key for this link.
        :param external: Whether the link is external.
        :param id_: The link’s id attribute’s value.
        :param data_attributes: Data attributes to add to the link.
        :return: The rendered link.
        """
        pass

    def render_wikicode(self, parsed_wikicode, context, enable_comment: bool = False) -> str:
        """Renders the given parsed wikicode (node tree).

        :param parsed_wikicode: The parsed wikicode, as a node tree.
        :type parsed_wikicode: WikiPy.parser.WikicodeNode
        :param context: Context of the page being rendered.
        :type context: WikiPy.page_context.PageContext
        :param enable_comment: If true, the generation comment will be appended to the rendered HTML.
        :return: The wikicode rendered as HTML.
        """
        start = time.time()
        render = parsed_wikicode.render(self, context)
        total = (time.time() - start) * 1000
        if enable_comment:
            comment = f"""
<!--
Page generated by WikiPy in {total:0.4} ms.
Skin: {self.name(context.language)}
-->"""
        else:
            comment = ''

        return render + comment


_loaded_skins = {}


def load_skin(name: str) -> bool:
    """Loads the skin with the given name.

    Skin subclasses must be defined in a package and define a load_skin() function
    that takes in the skins directory path and returns an instance of the skin’s class.

    :param name: The skin’s name.
    :return: True if the skin has been loaded, false otherwise.
    """
    logging.info(f'Loading skin "{name}"…')

    try:
        module = importlib.import_module('.' + name, package=__name__)
    except ModuleNotFoundError:  # Should never happen
        logging.error(f'Module "{__name__}.{name}" not found, skipping skin.')
        return False

    try:
        # noinspection PyUnresolvedReferences
        skin = module.load_skin(module.__path__[0])
    except AttributeError:
        logging.error(f'Missing "load_skin" function for skin "{name}", skipping skin.')
        return False
    except KeyError as e:
        logging.error(f'Missing key {e}, skipping skin.')
        return False
    except TypeError as e:
        logging.error(f'Type error, skipping skin: {e}.')
        return False
    except json.JSONDecodeError as e:
        logging.error(f'JSON error, skipping skin: {e}.')
        return False

    skin.load_translations()
    _loaded_skins[skin.id] = skin

    logging.info(f'Skin loaded successfully.')

    return True


def get_skin(ident: str) -> typ.Optional[Skin]:
    """Returns the skin with the given ID.

    :param ident: The skin’s ID.
    :return: The skin or None if the ID is not defined.
    """
    return _loaded_skins.get(ident)


def get_loaded_skins() -> typ.Iterable[Skin]:
    """Returns the list of all loaded skins."""
    return _loaded_skins.values()


__all__ = [
    'Skin',
    'load_skin',
    'get_skin',
    'get_loaded_skins',
]
