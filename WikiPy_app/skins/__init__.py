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

from .. import api, apps, settings, special_pages, page_context


@dataclasses.dataclass(frozen=True)
class MenuItem:
    item_id: str
    access_key: str
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


class PageTemplate:
    def __init__(self):
        self.__menus_links = {}

        with open(os.path.join(dj_settings.BASE_DIR, apps.WikiPyAppConfig.name, 'skins', 'page_template.json'),
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
        :type context: WikiPy_app.page_context.PageContext
        :return: The list of items for the given menu ID.
        """

        def f(item: MenuItem) -> bool:
            return ((not item.requires_page_exists or context.page_exists) and
                    (not item.requires_not_special_page or context.page.namespace.id != settings.SPECIAL_NS.id) and
                    (not item.requires_user_page or context.page.namespace.id in [settings.USER_NS.id,
                                                                                  settings.USER_TALK_NS.id]) and
                    (not item.requires_logged_in or context.user.is_logged_in) and
                    (not item.requires_logged_out or not context.user.is_logged_in) and
                    (not item.requires_user_can_read or context.user_can_read))

        return list(filter(f, self.__menus_links.get(menu_id, [])))


_PAGE_TEMPLATE = PageTemplate()


class Skin(abc.ABC):
    def __init__(self, name: str, label: str, **body_attrs: str):
        self.__name = name
        self.__label = label
        self.__body_attrs = dict(body_attrs)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def label(self) -> str:
        return self.__label

    @property
    def body_attrs(self):
        return dj_safe.mark_safe(' '.join(map(lambda e: f'{e[0]}="{e[1]}"', self.__body_attrs.items())))

    def get_rendered_menu_items(self, menu_id: str, context, *link_classes: str) -> typ.List[str]:
        """
        Returns the items for a specific menu ID.
        Items will be filtered using the given page context.

        :param menu_id: ID of the menu to return the items of.
        :param context: Context of the page being rendered.
        :type context: WikiPy_app.page_context.TemplateContext
        :param link_classes: Optional classes to apply to the HTML links.
        :return: The list of items for the given menu ID.
        """
        rendered_items = []
        c: page_context.PageContext = context['wpy_context']

        for item in _PAGE_TEMPLATE.get_menu_items(menu_id, c):
            args = {}

            if item.is_special:
                page = special_pages.get_special_page_for_id(item.item_id)
                ns_id = settings.SPECIAL_NS.id
                title = page.get_title()
                icon = page.icon
                access_key = page.access_key
                text = page.display_title(c.language)
                tooltip = c.language.translate(f'special.{page.id}.tooltip', none_if_undefined=True) or text

            else:
                item_id = item.item_id
                ns_id = c.page.namespace.id
                title = c.page.title
                icon = item.icon
                access_key = item.access_key
                text = c.language.translate(f'link.menu.{item_id}.label')
                tooltip = c.language.translate(f'link.menu.{item_id}.tooltip')

                if item_id == 'permalink':
                    args['revision_id'] = c.page.latest_revision.id

                elif item_id == 'read':
                    ns_id = api.get_base_page_namespace(ns_id)
                    if context.request.GET.get('revision_id'):
                        args['revision_id'] = context.request.GET['revision_id']

                elif item_id == 'talk':
                    ns_id = api.get_talk_page_namespace(ns_id)

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

                elif item_id == 'user_page':
                    ns_id = settings.USER_NS.id
                    title = c.user.username

                elif item_id == 'user_talk':
                    ns_id = settings.USER_TALK_NS.id
                    title = c.user.username

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
                page_title=api.get_full_page_title(ns_id, title),
                text=text,
                tooltip=tooltip,
                access_key=access_key if not item.disable_access_key else None,
                css_classes=link_classes,
                **args
            ))

        return rendered_items

    def format_internal_link(self, language, current_page_title: str, page_title: str,
                             text: str = None, tooltip: str = None, anchor: str = None, no_red_link: bool = False,
                             css_classes: typ.Sequence[str] = None, access_key: str = None, only_url: bool = False,
                             new_tab: bool = False, **url_params) -> str:
        ns_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
        page_exists = no_red_link or api.page_exists(ns_id, title)
        url = api.get_page_url(ns_id, title)
        link_text = text or page_title
        if tooltip is not None:
            link_tooltip = tooltip
        else:
            link_tooltip = page_title

        if current_page_title == page_title and not anchor and len(url_params) == 0:
            return f'<strong class="wpy-self-link">{link_text}</strong>' if not only_url else ''
        elif page_exists:
            if url_params == {}:
                if anchor:
                    url += '#' + anchor
            else:
                params = urllib.parse.urlencode(url_params)
                if params:
                    url += '?' + params
        elif ns_id != settings.SPECIAL_NS.id:
            url += '?action=edit&redlink=1'
            paren = language.translate('link.redlink.tooltip')
            link_tooltip += f' ({paren})'

        if not only_url:
            return self._format_link(url, link_text, link_tooltip, page_exists, css_classes or [], access_key,
                                     external=new_tab)
        else:
            return url

    def format_external_link(self, url: str, text: str = None, css_classes: typ.Sequence[str] = None) -> str:
        return self._format_link(url, text or url, tooltip=url, page_exists=True, css_classes=css_classes or [],
                                 external=True)

    @abc.abstractmethod
    def _format_link(self, url: str, text: str, tooltip: str, page_exists: bool, css_classes: typ.Sequence[str],
                     access_key: str = None, external: bool = False) -> str:
        pass

    def render_wikicode(self, parsed_wikicode, context, enable_comment: bool = False) -> str:
        """
        Renders the given parsed wikicode.
        :param parsed_wikicode: The parsed wikicode to render.
        :type parsed_wikicode: WikiPy_app.parser.WikicodeNode
        :param context: Context of the page being rendered.
        :type context: WikiPy_app.page_context.PageContext
        :param enable_comment: If true, the generation comment will be appended to the rendered HTML.
        :return: The wikicode rendered as HTML.
        """
        start = time.time()
        render = parsed_wikicode.render(self, context)
        total = (time.time() - start) * 1000
        if enable_comment:
            comment = f"""
<!--
Page generated by WikiPy in {total:0.4}\u00a0ms.
Skin: {self.label}
-->"""
        else:
            comment = ''

        return render + comment


_LOADED_SKINS = {}


def load_skin(name: str):
    try:
        module = importlib.import_module('._' + name, package=__name__)
        # noinspection PyUnresolvedReferences
        skin = module.load_skin()
        _LOADED_SKINS[skin.name] = skin
    except ModuleNotFoundError:  # Should never happen
        logging.warning(f'unknown skin name "{name}", ignored')


def get_skin(name: str) -> typ.Optional[Skin]:
    if name in _LOADED_SKINS:
        return _LOADED_SKINS[name]
    return None


def get_loaded_skins() -> typ.List[Skin]:
    return sorted(_LOADED_SKINS.values(), key=lambda s: s.label)


__all__ = [
    'Skin',
    'load_skin',
    'get_skin',
    'get_loaded_skins',
]
