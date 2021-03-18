import typing as typ

import django.template as dj_template
import django.templatetags.static as dj_static
import django.utils.safestring as dj_safe

from . import wpy_tags
from .. import page_context
from ..api import titles as api_titles

register = dj_template.Library()


@register.simple_tag(takes_context=True)
def wpy_skin_render(context: page_context.TemplateContext, key: str, **kwargs: typ.Dict[str, str]) \
        -> typ.Union[str, typ.List[str]]:
    wpy_context: page_context.PageContext = context.get('wpy_context')
    skin = wpy_context.skin
    language = wpy_context.language
    res = key

    if key == 'project_logo':
        main_page_link = api_titles.get_page_url(wpy_context.main_page_namespace.id, wpy_context.main_page_title)
        link_class = kwargs.get('link_class', '')
        image_class = kwargs.get('image_class', '')
        tooltip = language.translate('link.main_page.tooltip')
        image_source = dj_static.static('WikiPy/icons/wiki-logo.png')
        res = f'<a href="{main_page_link}" class="{link_class}" title="{tooltip}">' \
              f'<img src="{image_source}" class="{image_class}" alt="wiki logo" id="wpy-wiki-logo"/></a>'

    elif key == 'footer':
        res = ''
        if wpy_context.page.latest_revision:
            formatted_date = wpy_tags.wpy_format_date(context, wpy_context.page.latest_revision.date)
            last_edit = language.translate('footer.last_edit', date=formatted_date)
            res = f'<p>{last_edit}</p>'
        license_ = language.translate('footer.license')
        res += f'<p>{license_}</p>'

    else:
        levels = key.split('.')
        if levels[0] == 'menu':
            l2 = levels[2]
            if len(levels) == 3 and levels[1] == 'user' and l2 == 'items':
                res = skin.get_rendered_menu_items('user', context, *kwargs.get('links_class', '').split(' '))

            elif len(levels) == 4 and levels[1] == 'side':
                if levels[3] == 'title':
                    res = language.translate('menu.' + l2)
                elif levels[3] == 'items':
                    res = skin.get_rendered_menu_items(l2, context, *kwargs.get('links_class', '').split(' '))

            elif len(levels) == 3 and levels[1] == 'page' and l2 == 'items':
                res = skin.get_rendered_menu_items('page', context, *kwargs.get('links_class', '').split(' '))

    if isinstance(res, str):
        return dj_safe.mark_safe(res)
    return list(map(dj_safe.mark_safe, res))
