from . import Skin


def load_skin():
    class DefaultSkin(Skin):
        def __init__(self):
            super().__init__('default', 'Default Skin')

        def render_wikicode(self, parsed_wikicode) -> str:
            """
            Renders the given parsed wikicode.

            :param parsed_wikicode: The parsed wikicode to render.
            :type parsed_wikicode: django_wiki.api.ParsedWikicode
            :return: The parsed wikicode.
            """
            # TODO
            return str(parsed_wikicode)  # TEMP

    return DefaultSkin()
