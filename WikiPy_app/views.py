import django.http as dj_http
import django.shortcuts as dj_scut
from django.template import loader

from . import pages, api, apps


def page(request, page_title=''):
    if page_title == '':
        page_title = pages.get_main_page_title()
    namespace, title = api.extract_namespace_and_title(page_title, ns_as_id=True)

    context, error_code = pages.get_page(namespace, title, url_params={})

    if error_code == pages.NOT_FOUND:
        content = loader.render_to_string(apps.WikiPyAppConfig.name + '/base.html', context=context, request=request)
        return dj_http.HttpResponseNotFound(content)
    if error_code == pages.FORBIDDEN:
        content = loader.render_to_string(apps.WikiPyAppConfig.name + '/base.html', context=context, request=request)
        return dj_http.HttpResponseForbidden(content)
    return dj_scut.render(request, apps.WikiPyAppConfig.name + '/base.html', context=context)


def handler403(request, exception):
    pass  # TODO


def handler404(request, exception):
    pass  # TODO


def handler500(request, exception):
    pass  # TODO
