from . import SpecialPage, REDIRECTIONS_CAT
from .. import page_context, api, settings


class RandomPage(SpecialPage):
    def __init__(self):
        super().__init__('random_page', 'Random page', category=REDIRECTIONS_CAT, icon='dice-multiple', access_key='x')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        result = api.get_random_page(namespaces=settings.RANDOM_PAGE_NAMESPACES)
        if result:
            ns, title = result.namespace_id, result.title
        else:
            ns, title = settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE
        context = page_context.RedirectPageContext(base_context, to=api.get_full_page_title(ns, title))

        return context, [], None


def load_special_page() -> SpecialPage:
    return RandomPage()
