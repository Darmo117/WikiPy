import django.template as dj_template
import django.utils.safestring as dj_safe

from . import wpy_tags
from .. import page_context

register = dj_template.Library()


@register.inclusion_tag('WikiPy_app/tags/search-result.html', takes_context=True)
def search_results(context: page_context.TemplateContext):
    wpy_context: page_context.PageContext = context.get('wpy_context')
    paginator = wpy_context.paginator
    page = wpy_context.page

    results = []
    for result in paginator.get_page(page):
        link = dj_safe.mark_safe(wpy_tags.wpy_inner_link(context, result.namespace_id, result.title))
        results.append((link, result.date, result.snapshot))

    return {
        'wpy_context': wpy_context,
        'results': results,
        'url_params': context.get('request').GET,
    }
