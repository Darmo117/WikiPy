import dataclasses

from . import SpecialPage, PAGE_LISTS_CAT
from .. import page_context, api, forms, util, settings


@dataclasses.dataclass(init=False)
class SearchPageContext(page_context.PageContext):
    search_has_query: bool
    search_results_found: bool
    search_form: forms.SearchPageForm

    def __init__(self, context: page_context.PageContext, /, has_query: bool, search_results_found: bool,
                 form: forms.SearchPageForm):
        self._context = context
        self.search_has_query = has_query
        self.search_results_found = search_results_found
        self.search_form = form


class SearchPage(SpecialPage):
    def __init__(self):
        super().__init__('search', 'Search', category=PAGE_LISTS_CAT, has_js=True, has_css=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        user = api.get_user_from_request(request)
        results = []
        title = None
        search_bar = False

        default_namespaces = [settings.MAIN_NS.id]

        if len(sub_title) != 0:
            params = util.add_entries(request.GET, query="/".join(sub_title))
        else:
            params = request.GET

        if params.get('query'):
            has_query = True
            if not params.get('namespaces'):
                params = util.add_entries(params, namespaces=default_namespaces)
            form = forms.SearchPageForm(params)
            if form.is_valid():
                query = form.cleaned_data['query']
                namespaces = map(int, form.cleaned_data['namespaces'])
                search_bar = util.get_param(request.GET, 'search_bar', expected_type=bool, default=False)
                results = api.search(query, user, namespaces)
                title = base_context.language.translate('special.search.title_results', query=query)
        else:
            has_query = False
            form = forms.SearchPageForm(initial={'namespaces': default_namespaces})

        context = base_context
        if len(results) == 1 and search_bar:
            ns = results[0].namespace_id
            title = results[0].title
            context = page_context.RedirectPageContext(context, to=api.get_full_page_title(ns, title))
        else:
            context = SearchPageContext(
                context,
                has_query=has_query,
                search_results_found=len(results) != 0,
                form=form
            )

        return context, results, title


def load_special_page() -> SpecialPage:
    return SearchPage()
