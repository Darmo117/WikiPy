import logging
import urllib.parse as url_parse

import django.http as dj_http
import django.shortcuts as dj_scut

from . import pages, api, apps, web_api


def page(request, raw_page_title=''):
    # Redirect to main page if no page name
    if raw_page_title == '':
        return dj_scut.redirect('page', raw_page_title=api.as_url_title(pages.get_main_page_title()))

    # Get user info
    user = api.get_user(request)
    logging.debug(user.username)  # DEBUG

    # Get "correct" page title
    try:
        formatted_title = api.as_url_title(api.get_actual_page_title(api.title_from_url(raw_page_title)))
    except (api.BadTitleException, api.EmptyPageTitleException) as e:
        context = pages.get_bad_title_page(user, e)
        status = 400
    else:
        # Redirect to "correct" page title
        if formatted_title != raw_page_title:
            return dj_scut.redirect('page', raw_page_title=formatted_title)

        # Handle page
        page_title = api.title_from_url(raw_page_title)
        namespace_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
        params = request.GET
        post = request.POST
        action = params.get('action', 'read')
        try:
            redirect_enabled = not int(params.get('noredirect', 0))
        except ValueError:
            redirect_enabled = True

        if action == pages.SUBMIT:
            wikicode = post.get('wpy-edit-field')
            section_id = post.get('wpy-edit-section-id')
            try:
                section_id = int(section_id)
            except ValueError:
                section_id = None
            (context, status), redirect = pages.submit_page_content(namespace_id, title, user, wikicode,
                                                                    section_id=section_id)
            # FIXME detect redirect loops
            if status == pages.FOUND and redirect:
                return _redirect('page', api.get_full_page_title(namespace_id, title), noredirect=1)
        else:
            # Render page and send result
            context, status = pages.get_page(namespace_id, title, user, action=action,
                                             redirect_enabled=redirect_enabled)

    if type(context) == str:
        return _redirect('page', context)
    if context['mode'] == pages.READ:
        context['rendered_page_content'] = api.render_wikicode(context['wikicode'], user.data.skin)

    template_file = f'{apps.WikiPyAppConfig.name}/skins/{user.data.skin}.html'
    return dj_scut.render(request, template_file, context=context, status=status)


# TODO
def api_handler(request):
    user = api.get_user(request)
    context, page_type = web_api.handle_api(user, request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['result'], content_type=context['content_type'])
    else:
        return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/api/{page_type}.html', context=context)


def _redirect(url_name, *args, **kwargs):
    url = dj_scut.reverse(url_name, args=map(lambda arg: api.as_url_title(arg), args))
    params = url_parse.urlencode(kwargs)
    return dj_http.HttpResponseRedirect(url + ("?" + params if params else ""))


def handle403(request, _):
    context = {
        'url': request.path[1:],  # Remove / at index 0
    }
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/404.html', context=context, status=404)


def handle404(request):
    context = {
        'url': request.path[1:],  # Remove / at index 0
    }
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/404.html', context=context, status=404)


def handle500(request):
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/500.html', status=404)
