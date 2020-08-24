from . import SpecialPage


def load_special_page(settings) -> SpecialPage:
    class HideRevisions(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'hide_revisions', 'Hide revisions')

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            # TODO
            context = base_context

            return context, [], None

    return HideRevisions()
