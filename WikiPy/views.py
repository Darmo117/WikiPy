import json
import typing as typ
import urllib.parse as url_parse

import django.core.handlers.wsgi as dj_wsgi
import django.http as dj_http
import django.shortcuts as dj_scut
import django.utils.safestring as dj_safe
import slimit

from . import apps, web_api, setup, settings, page_context, models, util, skins, page_handlers, special_pages
from .api import titles as api_titles, pages as api_pages, users as api_users, errors as api_errors

# Session keys
SESSION_REDIRECTED_FROM = 'redirected_from'
SESSION_NO_REDIRECT = 'no_redirect'
# GET keys
GET_NO_REDIRECT = 'no_redirect'


def page(request: dj_wsgi.WSGIRequest, raw_page_title: str = '') -> dj_http.HttpResponse:
    # Redirect to setup page if wiki is not setup
    if not setup.are_pages_setup():
        setup_page_title = api_titles.as_url_title(
            api_titles.get_full_page_title(settings.SPECIAL_NS.id, settings.WIKI_SETUP_PAGE_TITLE))
        if raw_page_title != setup_page_title:
            return _redirect('page', setup_page_title)

    # Redirect to main page if no page name
    if raw_page_title == '':
        return _redirect('page', api_titles.as_url_title(
            api_titles.get_full_page_title(settings.MAIN_PAGE_NAMESPACE_ID, settings.MAIN_PAGE_TITLE)))

    params = request.GET

    user = api_users.get_user_from_request(request)
    language = _get_language(user, request)
    skin = _get_skin_id(user, request)

    # Get "correct" page title
    try:
        formatted_title = api_titles.as_url_title(
            api_titles.get_actual_page_title(api_titles.title_from_url(raw_page_title)))
    except (api_errors.BadTitleError, api_errors.EmptyPageTitleError) as e:
        if isinstance(e, api_errors.EmptyPageTitleError):
            title = special_pages.get_special_page_for_id('empty_title').title
            args = {}
        else:
            title = special_pages.get_special_page_for_id('bad_title').title
            args = {'invalid_char': str(e)}
        full_title = api_titles.get_full_page_title(settings.SPECIAL_NS.id, title)
        return _get_page(request, full_title, page_handlers.ACTION_READ, user, language, skin, override_status=400,
                         special_page_kwargs=args)

    # Redirect to "correct" page title while keeping GET parameters
    if formatted_title != raw_page_title:
        return _redirect('page', formatted_title, **params)

    page_title = api_titles.title_from_url(raw_page_title)

    # Extract action
    action = util.get_param(params, 'action')

    return _get_page(request, page_title, action, user, language, skin)


def _get_page(
        request: dj_wsgi.WSGIRequest,
        page_title: str,
        action: str,
        user: models.User,
        language: settings.i18n.Language,
        skin_id: str,
        override_status: int = None,
        special_page_kwargs: typ.Dict[str, typ.Any] = None
) -> dj_http.HttpResponse:
    namespace_id, title = api_titles.extract_namespace_and_title(page_title, ns_as_id=True)
    redirect_enabled = (not request.session.get(GET_NO_REDIRECT, False) and
                        not util.get_param(request.GET, GET_NO_REDIRECT, expected_type=bool, default=False))
    redirects_list = request.session.get(SESSION_REDIRECTED_FROM)
    # Reset session’s page-related params
    request.session[SESSION_NO_REDIRECT] = False

    if action not in page_handlers.ActionHandler.valid_actions():
        action = page_handlers.ACTION_READ
    action_handler = page_handlers.ActionHandler(
        action=action,
        request=request,
        namespace_id=namespace_id,
        title=title,
        user=user,
        language=language,
        skin_id=skin_id,
        redirect_enabled=redirect_enabled,
        redirects_list=redirects_list,
        special_page_kwargs=special_page_kwargs
    )
    context, status = action_handler.get_page_context()

    # Handle redirection pages
    if hasattr(context, 'redirect'):
        path = getattr(context, 'redirect')
        if not getattr(context, 'is_path', False):
            special_page_kwargs = {}
            if getattr(context, 'display_redirect'):
                if not request.session.get(SESSION_REDIRECTED_FROM):
                    request.session[SESSION_REDIRECTED_FROM] = []
                # Keep track of all cascading redirections
                request.session[SESSION_REDIRECTED_FROM].append(page_title)
            return _redirect('page', path, anchor=getattr(context, 'redirect_anchor'), **special_page_kwargs)
        else:
            return dj_scut.HttpResponseRedirect(path)
    else:
        # Reset redirects chain
        request.session[SESSION_REDIRECTED_FROM] = []

    status = override_status or status

    if action == page_handlers.ACTION_RAW and context.page.namespace_id != settings.SPECIAL_NS.id:
        return _get_raw(request, context, status)

    return _render(request, context, status)


# TODO cache and minify js and css
def _get_raw(request: dj_wsgi.WSGIRequest, context: page_context.PageContext, status: int) -> dj_http.HttpResponse:
    content = context.wikicode if status == page_handlers.STATUS_FOUND and hasattr(context, 'wikicode') else ''
    content_type = api_pages.get_page_content_type(context.page.content_model)
    return dj_http.HttpResponse(content, content_type=content_type, status=status)


def _render(request: dj_wsgi.WSGIRequest, wpy_context: page_context.PageContext, status: int):
    context = {
        'wpy_context': wpy_context,
        'js_data': dj_safe.mark_safe(_generate_js(wpy_context)),
    }
    for ns in settings.NAMESPACES.values():
        context[f'NS_{ns.canonical_name.upper()}'] = ns.id

    template_file = f'{apps.WikiPyConfig.name}/skins/{wpy_context.skin.id}/base.html'
    return dj_scut.render(request, template_file, context=context, status=status)


def api_handler(request: dj_wsgi.WSGIRequest):
    user = api_users.get_user_from_request(request)
    context, page_type = web_api.handle_api(user, request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['content'], content_type=context['content_type'])
    else:
        return dj_scut.render(request, f'{apps.WikiPyConfig.name}/api/{page_type}.html', context=context)


##########
# Errors #
##########


def handle404(request: dj_wsgi.WSGIRequest):
    context = {
        'url': request.path[1:],  # Remove / at index 0
    }
    return dj_scut.render(request, f'{apps.WikiPyConfig.name}/errors/404.html', context=context, status=404)


def handle500(request: dj_wsgi.WSGIRequest):
    return dj_scut.render(request, f'{apps.WikiPyConfig.name}/errors/500.html', status=500)


########
# Util #
########


def _redirect(url_name: str, *args, anchor: str = None, **kwargs) -> dj_http.HttpResponseRedirect:
    url = dj_scut.reverse('wikipy:' + url_name, args=map(lambda arg: api_titles.as_url_title(arg), args))
    params = url_parse.urlencode({k: (v if not isinstance(v, list) else v[0]) for k, v in kwargs.items()})
    full_url = url + (('?' + params) if params else '') + (('#' + anchor) if anchor else '')
    return dj_http.HttpResponseRedirect(full_url)


def _get_language(user: models.User, request: dj_wsgi.WSGIRequest) -> settings.i18n.Language:
    language = settings.i18n.get_language(util.get_param(request.GET, 'use_lang'))
    if not language:
        language = user.prefered_language
    return language


def _get_skin_id(user: models.User, request: dj_wsgi.WSGIRequest) -> str:
    skin_id = util.get_param(request.GET, 'use_skin')
    if not skin_id or not skins.get_skin(skin_id):
        skin_id = user.data.skin
    return skin_id


def _generate_js(context: page_context.PageContext) -> str:
    language = context.language
    ns_name_to_id = {}
    ns_id_to_name = {}
    for ns_id, ns in settings.NAMESPACES.items():
        ns_id_to_name[str(ns_id)] = ns.get_name(local=True)
        ns_name_to_id[ns.get_name(local=False)] = ns_id
        ns_name_to_id[ns.get_name(local=True)] = ns_id
        if ns.alias:
            ns_name_to_id[ns.alias] = ns_id

    url_path = api_titles.get_wiki_url_path()
    api_url_path = api_titles.get_api_url_path()
    groups = {g.name: g.label(context.language) for g in settings.GROUPS.values()}

    return slimit.minify(f"""
window.WPY_CONF = {{
    wpyPageTitle: "{context.page.title}",
    wpyUrlPageTitle: "{context.page.url_title}",
    wpyFullPageTitle: "{context.page.full_title}",
    wpyUrlFullPageTitle: "{context.page.url_full_title}",
    wpySpecialPageTitle: "{getattr(context, 'special_page_title', '')}",
    wpyUrlSpecialPageTitle: "{getattr(context, 'url_special_page_title', '')}",
    wpyCanonicalSpecialPageTitle: "{getattr(context, 'canonical_special_page_title', '')}",
    wpyUrlCanonicalSpecialPageTitle: "{getattr(context, 'url_canonical_special_page_title', '')}",
    wpyCanonicalNamespaceName: "{context.page.namespace.get_name(local=False)}",
    wpyUrlCanonicalNamespaceName: "{context.page.namespace.get_name(local=False, as_url=True)}",
    wpyNamespaceName: "{context.page.namespace.get_name(local=True)}",
    wpyUrlNamespaceName: "{context.page.namespace.get_name(local=True, as_url=True)}",
    wpyNamespaceId: "{context.page.namespace_id}",
    wpyUserName: "{context.user.username}",
    wpyUserGroups: {context.user.group_ids},
    wpyUserId: "{context.user.django_user.id}",
    wpyUserIsLoggedIn: {str(context.user.is_logged_in).lower()},
    wpyAction: "{context.mode}",
    wpySkin: "{context.skin.id}",
    wpyLanguageCode: "{language.code}",
    wpyLanguageCodes: {[lang.name for lang in context.languages]},
    wpyWritingDirection: "{language.writing_direction}",
    wpyContentModel: "{context.page.content_model}",
    wpyMainNamespaceName: "{language.main_namespace_name}",
    wpyAllNamespacesName: "{language.translate('form.all_namespaces')}",
    wpyNamespaces: {ns_id_to_name},
    wpyNamespacesIds: {ns_name_to_id},
    wpyGroups: {groups},
    wpyUrlPath: "{url_path}",
    wpyApiUrlPath: "{api_url_path}",
    wpyTranslations: {json.dumps(language.javascript_mappings)}
}};
""")
