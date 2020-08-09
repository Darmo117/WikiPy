import urllib.parse as url_parse

import django.http as dj_http
import django.shortcuts as dj_scut
import django.utils.safestring as dj_safe

from . import pages, api, apps, web_api, setup


def setup_page(request):
    if not setup.are_pages_setup():
        if request.GET.get('action') == 'setup':
            username = str(request.POST.get('wpy-setup-username', '')).strip()
            password = str(request.POST.get('wpy-setup-password', '')).strip()
            email = str(request.POST.get('wpy-setup-email', '')).strip()
            secret_key = str(request.POST.get('wpy-setup-secretkey', '')).strip()
            status = setup.setup(username, password, email, secret_key)

            if status != setup.SUCCESS:
                return _setup(
                    request,
                    invalid_username=status == setup.INVALID_USERNAME,
                    invalid_password=status == setup.INVALID_PASSWORD,
                    invalid_email=status == setup.INVALID_EMAIL,
                    invalid_secret_key=status == setup.INVALID_SECRET_KEY,
                    username=username,
                    email=email
                )
        else:
            return _setup(request)
    return _redirect('main_page')


def _setup(request, invalid_username=False, invalid_password=False, invalid_email=False, invalid_secret_key=False,
           username=None, email=None):
    user = api.get_user_from_request(request)
    context = {
        **pages.get_setup_page(user),
        'invalid_username': invalid_username,
        'invalid_password': invalid_password,
        'invalid_email': invalid_email,
        'invalid_secret_key': invalid_secret_key,
        'wpy_setup_username': username,
        'wpy_setup_email': email,
    }
    return _render(request, context, pages.FOUND, user)


def page(request, raw_page_title=''):
    # Redirect to setup page if wiki is not setup
    if not setup.are_pages_setup():
        return _redirect('setup')

    # Redirect to main page if no page name
    if raw_page_title == '':
        return _redirect('page', api.as_url_title(pages.get_main_page_title()))

    user = api.get_user_from_request(request)

    # Get "correct" page title
    try:
        formatted_title = api.as_url_title(api.get_actual_page_title(api.title_from_url(raw_page_title)))
    except (api.BadTitleException, api.EmptyPageTitleException) as e:
        return _render(request, pages.get_bad_title_page(user, e), 400, user)

    params = request.GET

    # Redirect to "correct" page title while keeping GET parameters
    if formatted_title != raw_page_title:
        return _redirect('page', formatted_title, **params)

    page_title = api.title_from_url(raw_page_title)

    # Extract action
    action = api.get_param(params, 'action', default='read')

    return _get_page(request, page_title, action, user)


def _get_page(request, page_title: str, action: str, user):
    namespace_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
    redirect_enabled = not api.get_param(request.GET, 'noredirect', expected_type=bool, default=False)

    post = request.POST

    if action == pages.SUBMIT and len(post) != 0:
        wikicode = api.get_param(post, 'wpy-edit-field', default='')
        section_id = api.get_param(post, 'wpy-edit-section-id', expected_type=int)
        comment = api.get_param(post, 'wpy-edit-revision-comment', default='')
        minor = api.get_param(post, 'wpy-edit-minor', expected_type=bool, default=False)
        (context, status), redirect = pages.submit_page_content(request, namespace_id, title, user, wikicode, comment,
                                                                minor, section_id=section_id)
        # FIXME detect redirect loops
        if status == pages.FOUND and redirect:
            return _redirect('page', api.get_full_page_title(namespace_id, title), noredirect=1)
    else:
        # Render page and send result
        context, status = pages.get_page(request, namespace_id, title, user, action=action,
                                         redirect_enabled=redirect_enabled)

    # Handle redirection pages
    if isinstance(context, str):
        return _redirect('page', context)

    if action == 'raw' and context['namespace_id'] != -1:
        return _get_raw(request, context, status)

    return _render(request, context, status, user)


# TODO minify js and css
def _get_raw(request, context, status):
    content = context['wikicode'] if status == pages.FOUND else ''
    title = context['page_title']
    content_type = 'plain'
    if title.endswith('.css'):
        content_type = 'css'
    elif title.endswith('.js'):
        content_type = 'js'
    return dj_http.HttpResponse(content, content_type='text/' + content_type, status=status)


def _render(request, context: dict, status: int, user):
    if context['mode'] == pages.READ:
        if 'wikicode' in context:
            context['rendered_page_content'] = dj_safe.mark_safe(
                api.render_wikicode(context['wikicode'], user.data.skin))
    if 'edit_notice' in context:
        context['edit_notice'] = dj_safe.mark_safe(
            api.render_wikicode(context['edit_notice'], user.data.skin))

    template_file = f'{apps.WikiPyAppConfig.name}/skins/{user.data.skin}/base.html'
    return dj_scut.render(request, template_file, context=context, status=status)


# TODO
def api_handler(request):
    user = api.get_user_from_request(request)
    context, page_type = web_api.handle_api(user, request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['result'], content_type=context['content_type'])
    else:
        return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/api/{page_type}.html', context=context)


def _redirect(url_name, *args, **kwargs):
    url = dj_scut.reverse(url_name, args=map(lambda arg: api.as_url_title(arg), args))
    params = url_parse.urlencode(kwargs)
    return dj_http.HttpResponseRedirect(url + (("?" + params) if params else ""))


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
