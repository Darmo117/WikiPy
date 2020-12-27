from .. import Skin


class DefaultSkin(Skin):
    def __init__(self, path: str):
        super().__init__(path, 'default', **{'class': 'd-flex flex-column'})

    def _format_link(self, url, text, tooltip, page_exists, css_classes, access_key=None, external=False):
        if not page_exists:
            css_classes = [*css_classes, 'wpy-redlink']
        attributes = []
        if 'disabled' in css_classes:
            attributes.append('aria-disabled="true"')
            url = ''
        if access_key:
            attributes.append(f'accesskey="{access_key}"')
        if external:
            text += ' <span class="mdi mdi-open-in-new"></span>'
            attributes.append(f'target="_blank"')
        link = f'<a href="{url}" class="{" ".join(css_classes)}" title="{tooltip}" {" ".join(attributes)}>{text}</a>'

        return link


def load_skin(path: str):
    return DefaultSkin(path)
