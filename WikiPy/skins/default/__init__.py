"""This module defines the default skin used by WikiPy."""
from .. import Skin


class DefaultSkin(Skin):
    def __init__(self, path: str):
        """The defaut skin used by WikiPy.

        :param path: The skins’ directory path.
        """
        super().__init__(path, 'default', **{'class': 'd-flex flex-column'})

    def _format_link(self, url, text, tooltip, page_exists, css_classes, access_key=None, external=False, id_=None,
                     **data_attributes):
        if not page_exists:
            css_classes = [*css_classes, 'wpy-redlink']
        attributes = {}
        if 'disabled' in css_classes:
            attributes['aria-disabled'] = 'true'
            url = ''
        if access_key:
            attributes['accesskey'] = access_key
        if external:
            text += ' <span class="mdi mdi-open-in-new"></span>'
            attributes['target'] = '_blank'
        for k, v in data_attributes.items():
            attributes[f'data-{k}'] = int(v) if isinstance(v, bool) else v
        if id_:
            attributes['id'] = id_
        attributes['href'] = url
        attributes['class'] = ' '.join(css_classes)
        attributes['title'] = tooltip
        attrs = ' '.join(f'{attr}="{value}"' for attr, value in attributes.items())
        link = f'<a {attrs}>{text}</a>'

        return link


def load_skin(path: str):
    return DefaultSkin(path)
