import urllib.parse as url_parse

import django.http as dj_http
import django.shortcuts as dj_scut
import django.utils.safestring as dj_safe
import slimit

from . import pages, api, apps, web_api, setup, settings, page_context


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
            setup.generate_secret_key_file()
            return _setup(request)
    return _redirect('main_page')


def _setup(request, invalid_username=False, invalid_password=False, invalid_email=False, invalid_secret_key=False,
           username=None, email=None):
    user = api.get_user_from_request(request)
    context = page_context.SetupPageContext(
        pages.get_setup_page(user),
        setup_invalid_username=invalid_username,
        setup_invalid_password=invalid_password,
        setup_invalid_email=invalid_email,
        setup_invalid_secret_key=invalid_secret_key,
        setup_username=username,
        setup_email=email
    )
    return _render(request, context, pages.FOUND, user)


def page(request, raw_page_title='') -> dj_http.HttpResponse:
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
        return _render(request, pages.get_bad_title_page(user, e, request), 400, user)

    params = request.GET

    # Redirect to "correct" page title while keeping GET parameters
    if formatted_title != raw_page_title:
        return _redirect('page', formatted_title, **params)

    page_title = api.title_from_url(raw_page_title)

    # Extract action
    action = api.get_param(params, 'action', default='read')

    return _get_page(request, page_title, action, user)


def _get_page(request, page_title: str, action: str, user) -> dj_http.HttpResponse:
    get = request.GET
    post = request.POST

    namespace_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
    redirect_enabled = not api.get_param(get, 'no_redirect', expected_type=bool, default=False)

    if namespace_id != -1 and action == pages.SUBMIT and len(post) != 0:
        wikicode = api.get_param(post, 'wpy-edit-field', default='')
        section_id = api.get_param(post, 'wpy-edit-section-id', expected_type=int)
        comment = api.get_param(post, 'wpy-edit-revision-comment', default='')
        minor = api.get_param(post, 'wpy-edit-minor', expected_type=bool, default=False)
        (context, status), redirect = pages.submit_page_content(request, namespace_id, title, user, wikicode, comment,
                                                                minor, section_id=section_id)
        # FIXME detect redirect loops
        if status == pages.FOUND and redirect:
            return _redirect('page', api.get_full_page_title(namespace_id, title))
    else:
        # Render page and send result
        context, status = pages.get_page(request, namespace_id, title, user, action=action,
                                         redirect_enabled=redirect_enabled)

    # Handle redirection pages
    if isinstance(context, str):
        return _redirect('page', context)

    if action == 'raw' and context.namespace_id != -1:
        return _get_raw(request, context, status)

    return _render(request, context, status, user)


# TODO cache and minify js and css
def _get_raw(request, context: page_context.PageContext, status: int) -> dj_http.HttpResponse:
    content = context.wikicode if status == pages.FOUND and hasattr(context, 'wikicode') else ''
    content_type = api.get_page_content_type(context.page_title)
    return dj_http.HttpResponse(content, content_type=content_type, status=status)


def _render(request, wpy_context: page_context.PageContext, status: int, user):
    context = {
        'wpy_context': wpy_context,
        'js_data': dj_safe.mark_safe(_generate_js(wpy_context)),
    }

    template_file = f'{apps.WikiPyAppConfig.name}/skins/{user.data.skin}/base.html'
    return dj_scut.render(request, template_file, context=context, status=status)


# TODO
def api_handler(request):
    # TODO enabled API deactivation
    user = api.get_user_from_request(request)
    context, page_type = web_api.handle_api(user, request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['result'], content_type=context['content_type'])
    else:
        return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/api/{page_type}.html', context=context)


def _redirect(url_name, *args, **kwargs) -> dj_http.HttpResponseRedirect:
    url = dj_scut.reverse(url_name, args=map(lambda arg: api.as_url_title(arg), args))
    params = url_parse.urlencode(kwargs)
    return dj_http.HttpResponseRedirect(url + (("?" + params) if params else ""))


def handle404(request):
    context = {
        'url': request.path[1:],  # Remove / at index 0
    }
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/404.html', context=context, status=404)


def handle500(request):
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/500.html', status=404)


def _generate_js(context: page_context.PageContext) -> str:
    ns_name_to_id = {}
    ns_id_to_name = {}
    for ns_id, ns in settings.NAMESPACES.items():
        ns_id_to_name[str(ns_id)] = ns.get_name(local=True)
        ns_name_to_id[ns.get_name(local=False)] = ns_id
        ns_name_to_id[ns.get_name(local=True)] = ns_id
        if ns.alias:
            ns_name_to_id[ns.alias] = ns_id

    url_path = dj_scut.reverse('page', args=[''])

    return slimit.minify(f"""
window.WPY_CONF = {{
    wpyPageTitle: "{context.page_title}",
    wpyUrlPageTitle: "{context.page_title_url}",
    wpyFullPageTitle: "{context.full_page_title}",
    wpyUrlFullPageTitle: "{context.full_page_title_url}",
    wpySpecialPageTitle: "{getattr(context, 'special_page_title', '')}",
    wpyUrlSpecialPageTitle: "{getattr(context, 'url_special_page_title', '')}",
    wpyCanonicalSpecialPageTitle: "{getattr(context, 'canonical_special_page_title', '')}",
    wpyUrlCanonicalSpecialPageTitle: "{getattr(context, 'url_canonical_special_page_title', '')}",
    wpyCanonicalNamespaceName: "{context.canonical_namespace_name}",
    wpyUrlCanonicalNamespaceName: "{context.canonical_namespace_name_url}",
    wpyNamespaceName: "{context.namespace_name}",
    wpyUrlNamespaceName: "{context.namespace_name_url}",
    wpyNamespaceId: "{context.namespace_id}",
    wpyUserName: "{context.user.username}",
    wpyUserGroups: {context.user.group_ids},
    wpyUserId: "{context.user.django_user.id}",
    wpyUserIsLoggedIn: {str(context.user.is_logged_in).lower()},
    wpyAction: "{context.mode}",
    wpySkin: "{context.skin_name}",
    wpyLanguageCode: "{context.language}",
    wpyWritingDirection: "{context.writing_direction}",
    wpyContentType: "{context.content_type}",
    wpyMainNamespaceName: "{settings.MAIN_NAMESPACE_NAME}",
    wpyNamespaces: {ns_id_to_name},
    wpyNamespacesIds: {ns_name_to_id},
    wpyGroups: {list(settings.GROUPS.keys())},
    wpyGroupNames: {[g.label for g in settings.GROUPS.values()]},
    wpyUrlPath: "{url_path}",
}};
""")
