import django.http as dj_http
import django.shortcuts as dj_scut
from django.template import loader

from . import pages, api, apps, web_api

HTML_PAGE = apps.WikiPyAppConfig.name + '/base.html'


def page(request, raw_page_title=''):
    # Redirect to main page if no page name
    if raw_page_title == '':
        return dj_scut.redirect('page', raw_page_title=api.as_url_title(pages.get_main_page_title()))

    try:
        formatted_title = api.as_url_title(api.get_actual_page_title(api.title_from_url(raw_page_title)))
    except (api.BadTitleException, api.EmptyPageTitleException) as e:
        return dj_scut.render(request, HTML_PAGE, context=pages.get_bad_title_page(e))

    # Redirect to correct page title
    if formatted_title != raw_page_title:
        return dj_scut.redirect('page', raw_page_title=formatted_title)

    # Handle page
    page_title = api.title_from_url(raw_page_title)
    namespace_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)

    context, error_code = pages.get_page(namespace_id, title, url_params={})

    if error_code == pages.NOT_FOUND:
        content = loader.render_to_string(HTML_PAGE, context=context, request=request)
        return dj_http.HttpResponseNotFound(content)
    if error_code == pages.FORBIDDEN:
        content = loader.render_to_string(HTML_PAGE, context=context, request=request)
        return dj_http.HttpResponseForbidden(content)
    return dj_scut.render(request, HTML_PAGE, context=context)


def api_handler(request):
    context, page_type = web_api.handle_api(request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['result'], content_type=context['content_type'])
    else:
        page_name = {
            web_api.HELP_PAGE: 'api_help',
            web_api.RESULT_PAGE: 'api_result',
        }[page_type]

        return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/{page_name}.html', context=context)


def handler403(request, exception):
    pass  # TODO


def handler404(request, exception):
    pass  # TODO


def handler500(request):
    pass  # TODO
