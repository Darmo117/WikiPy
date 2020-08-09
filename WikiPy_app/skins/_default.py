from . import Skin


def load_skin(settings):
    class DefaultSkin(Skin):
        def __init__(self):
            super().__init__('default', 'Default Skin', settings)

        def _format_link(self, api, url: str, text: str, tooltip: str, page_exists: bool):
            css_classes = 'wpy-redlink' if not page_exists else ''
            return f'<a href="{url}" class="{css_classes}" title="{tooltip}">{text}</a>'

        def _render_wikicode_impl(self, api, parsed_wikicode) -> str:
            """
            Renders the given parsed wikicode.

            :param parsed_wikicode: The parsed wikicode to render.
            :type parsed_wikicode: django_wiki.api.ParsedWikicode
            :return: The parsed wikicode.
            """
            # TODO
            return str(parsed_wikicode)  # TEMP

    return DefaultSkin()
