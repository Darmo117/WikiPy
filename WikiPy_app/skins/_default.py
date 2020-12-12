from . import Skin


class DefaultSkin(Skin):
    def __init__(self):
        super().__init__('default', 'Default Skin', **{'class': 'd-flex flex-column'})

    def _format_link(self, url, text, tooltip, page_exists, css_classes, access_key=None, external=None):
        if not page_exists:
            css_classes += ['wpy-redlink']
        attributes = []
        if 'disabled' in css_classes:
            attributes.append('aria-disabled="true"')
            url = ''
        if access_key:
            attributes.append(f'accesskey="{access_key}"')
        if external:
            text += ' <span class="mdi mdi-open-in-new"></span>'
        link = f'<a href="{url}" class="{" ".join(css_classes)}" title="{tooltip}" {" ".join(attributes)}>{text}</a>'

        return link


def load_skin():
    return DefaultSkin()
