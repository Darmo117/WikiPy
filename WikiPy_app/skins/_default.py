import typing as typ

from . import Skin


def load_skin(settings):
    class DefaultSkin(Skin):
        def __init__(self):
            super().__init__('default', 'Default Skin', settings)

        def _format_link(self, api, url: str, text: str, tooltip: str, page_exists: bool, css_classes: typ.List[str],
                         access_key: str = None):
            if not page_exists:
                css_classes += ['wpy-redlink']
            attributes = []
            if 'disabled' in css_classes:
                attributes.append('aria-disabled="true"')
                url = ''
            if access_key:
                attributes.append(f'accesskey="{access_key}"')
            return f'<a href="{url}" class="{" ".join(css_classes)}" title="{tooltip}" ' \
                   f'{" ".join(attributes)}>{text}</a>'

        def _render_wikicode_impl(self, api, parsed_wikicode) -> str:
            """
            Renders the given parsed wikicode.

            :param parsed_wikicode: The parsed wikicode to render.
            :type parsed_wikicode: django_wiki.api.ParsedWikicode
            :return: The parsed wikicode.
            """
            # TODO
            return str(parsed_wikicode.replace('\n', '<br/>'))  # TEMP

    return DefaultSkin()
