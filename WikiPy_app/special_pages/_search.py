import dataclasses
import typing as typ

from . import SpecialPage, RedirectPageContext
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class SearchPageContext(page_context.PageContext):
        search_query: str
        search_results_found: bool
        search_namespace_ids: typ.List[int]

        def __init__(self, context: page_context.PageContext, /, search_query: str, search_results_found: bool,
                     search_namespace_ids: typ.List[int]):
            self._context = context
            self.search_query = search_query
            self.search_results_found = search_results_found
            self.search_namespace_ids = search_namespace_ids

    class SearchPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'search', 'Search', has_js=True)

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            user = api.get_user_from_request(request)
            namespaces = []
            results = []
            title = None
            search_bar = False

            if len(sub_title) != 0:
                query = "/".join(sub_title)
            else:
                query = api.get_param(request.GET, 'query')

            if query:
                namespaces = api.get_param(request.GET, 'namespaces', is_list=True, expected_type=int)
                search_bar = api.get_param(request.GET, 'search_bar', expected_type=bool, default=False)
                if not namespaces:
                    namespaces = [0]
                results = api.search(query, user, namespaces)
                title = self._settings.i18n.trans('special.search.title_results', query=query)

            context = base_context
            if len(results) == 1 and search_bar:
                ns = results[0].namespace_id
                title = results[0].title
                context = RedirectPageContext(context, to=api.get_full_page_title(ns, title))
            else:
                context = SearchPageContext(
                    context,
                    search_query=query if query else '',
                    search_results_found=len(results) != 0,
                    search_namespace_ids=namespaces
                )

            return context, results, title

    return SearchPage()
