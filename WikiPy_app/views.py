import json
import typing as typ
import urllib.parse as url_parse

import django.core.handlers.wsgi as dj_wsgi
import django.http as dj_http
import django.shortcuts as dj_scut
import django.utils.safestring as dj_safe
import slimit

from . import pages, api, apps, web_api, setup, settings, page_context, forms, models, util, skins

# Session keys
SESSION_REDIRECTED_FROM = 'redirected_from'
SESSION_NO_REDIRECT = 'no_redirect'
# Get keys
GET_NO_REDIRECT = 'no_redirect'


def setup_page(request: dj_wsgi.WSGIRequest) -> dj_http.HttpResponse:
    if not setup.are_pages_setup():
        user = api.get_user_from_request(request)
        language = _get_language(user, request)
        if request.method == 'POST':
            form = forms.SetupPageForm(request.POST)
            success = False
            errors = []
            if form.is_valid():
                if form.passwords_match():
                    username = form.cleaned_data['username']
                    password = form.cleaned_data['password']
                    email = form.cleaned_data['email']
                    secret_key = form.cleaned_data['secret_key']
                    status = setup.setup(request, username, password, email, secret_key)

                    if status != setup.SUCCESS:
                        errors.append(status)
                    else:
                        success = True
                else:
                    errors.append('passwords_mismatch')
            if not success:
                return _setup(request, language, 'default', form, errors)
        else:
            setup.generate_secret_key_file()
            return _setup(request, language, 'default', forms.SetupPageForm())
    return _redirect('main_page')


def _setup(
        request: dj_wsgi.WSGIRequest,
        language: settings.i18n.Language,
        skin: str,
        form: forms.SetupPageForm,
        errors: typ.List[str] = None
) -> dj_http.HttpResponse:
    user = api.get_user_from_request(request)
    context = page_context.SetupPageContext(pages.get_setup_page_context(request, user, language, skin), form=form,
                                            global_errors=errors)
    return _render(request, context, pages.FOUND, skin)


def page(request: dj_wsgi.WSGIRequest, raw_page_title: str = '') -> dj_http.HttpResponse:
    # Redirect to setup page if wiki is not setup
    if not setup.are_pages_setup():
        return _redirect('setup')

    # Redirect to main page if no page name
    if raw_page_title == '':
        return _redirect('page', api.as_url_title(pages.get_main_page_title()))

    params = request.GET

    user = api.get_user_from_request(request)
    language = _get_language(user, request)
    skin = _get_skin(user, request)

    # Get "correct" page title
    try:
        formatted_title = api.as_url_title(api.get_actual_page_title(api.title_from_url(raw_page_title)))
    except (api.BadTitleException, api.EmptyPageTitleException) as e:
        return _render(request, pages.get_bad_title_page(user, language, skin, e, request), 400, skin)

    # Redirect to "correct" page title while keeping GET parameters
    if formatted_title != raw_page_title:
        return _redirect('page', formatted_title, **params)

    page_title = api.title_from_url(raw_page_title)

    # Extract action
    action = util.get_param(params, 'action', default='read')

    return _get_page(request, page_title, action, user, language, skin)


def _get_page(
        request: dj_wsgi.WSGIRequest,
        page_title: str,
        action: str,
        user: models.User,
        language: settings.i18n.Language,
        skin: str
) -> dj_http.HttpResponse:
    namespace_id, title = api.extract_namespace_and_title(page_title, ns_as_id=True)
    redirect_enabled = (not request.session.get(GET_NO_REDIRECT, False) and
                        not util.get_param(request.GET, GET_NO_REDIRECT, expected_type=bool, default=False))
    redirects_list = request.session.get(SESSION_REDIRECTED_FROM)
    # Reset session???s page-related params
    request.session[SESSION_NO_REDIRECT] = False

    if namespace_id != settings.SPECIAL_NS.id and action == pages.SUBMIT and len(request.POST) != 0:
        form = forms.EditPageForm(request.POST, warn_unsaved_changes=user.data.unsaved_changes_warning)
        if form.is_valid():
            wikicode = form.cleaned_data['content']
            section_id = form.cleaned_data['section_id']
            if section_id:
                try:
                    section_id = int(section_id)
                except ValueError:
                    section_id = None
            else:
                section_id = None
            comment = form.cleaned_data['comment']
            minor = form.cleaned_data['minor_edit']
            # noinspection PyUnusedLocal
            follow_page = form.cleaned_data['follow_page']  # TODO
            hidden_category = form.cleaned_data['hidden_category']
            (context, status), redirect = pages.submit_page_content(
                request,
                namespace_id,
                title,
                user,
                wikicode,
                comment,
                minor,
                language,
                section_id=section_id,
                hidden_category=hidden_category
            )
            if status == pages.FOUND and redirect:
                request.session[SESSION_NO_REDIRECT] = True
                return _redirect('page', api.get_full_page_title(namespace_id, title))
        else:
            context, status = pages.get_page_context(
                request,
                namespace_id,
                title,
                user,
                language,
                skin,
                action=pages.EDIT,
                redirect_enabled=redirect_enabled,
                form=form
            )
    else:
        context, status = pages.get_page_context(
            request,
            namespace_id,
            title,
            user,
            language,
            skin,
            action=action,
            redirect_enabled=redirect_enabled,
            redirects_list=redirects_list
        )

    # Handle redirection pages
    if hasattr(context, 'redirect'):
        path = getattr(context, 'redirect')
        if not getattr(context, 'is_path', False):
            kwargs = {}
            if getattr(context, 'display_redirect'):
                if not request.session.get(SESSION_REDIRECTED_FROM):
                    request.session[SESSION_REDIRECTED_FROM] = []
                # Keep track of all cascading redirections
                request.session[SESSION_REDIRECTED_FROM].append(page_title)
            return _redirect('page', path, anchor=getattr(context, 'redirect_anchor'), **kwargs)
        else:
            return dj_scut.HttpResponseRedirect(path)
    else:
        # Reset redirects chain
        request.session[SESSION_REDIRECTED_FROM] = []

    if action == 'raw' and context.page.namespace_id != settings.SPECIAL_NS.id:
        return _get_raw(request, context, status)

    return _render(request, context, status, skin)


# TODO cache and minify js and css
def _get_raw(request: dj_wsgi.WSGIRequest, context: page_context.PageContext, status: int) -> dj_http.HttpResponse:
    content = context.wikicode if status == pages.FOUND and hasattr(context, 'wikicode') else ''
    content_type = api.get_page_content_type(context.page.content_model)
    return dj_http.HttpResponse(content, content_type=content_type, status=status)


def _render(request: dj_wsgi.WSGIRequest, wpy_context: page_context.PageContext, status: int, skin: str):
    context = {
        'wpy_context': wpy_context,
        'js_data': dj_safe.mark_safe(_generate_js(wpy_context)),
    }

    template_file = f'{apps.WikiPyAppConfig.name}/skins/{skin}/base.html'
    return dj_scut.render(request, template_file, context=context, status=status)


def api_handler(request: dj_wsgi.WSGIRequest):
    user = api.get_user_from_request(request)
    context, page_type = web_api.handle_api(user, request.GET)

    if page_type == web_api.RAW_RESULT:
        return dj_http.HttpResponse(content=context['content'], content_type=context['content_type'])
    else:
        return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/api/{page_type}.html', context=context)


##########
# Errors #
##########


def handle404(request: dj_wsgi.WSGIRequest):
    context = {
        'url': request.path[1:],  # Remove / at index 0
    }
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/404.html', context=context, status=404)


def handle500(request: dj_wsgi.WSGIRequest):
    return dj_scut.render(request, f'{apps.WikiPyAppConfig.name}/errors/500.html', status=500)


########
# Util #
########


def _redirect(url_name: str, *args, anchor: str = None, **kwargs) -> dj_http.HttpResponseRedirect:
    url = dj_scut.reverse('wikipy:' + url_name, args=map(lambda arg: api.as_url_title(arg), args))
    params = url_parse.urlencode({k: (v if not isinstance(v, list) else v[0]) for k, v in kwargs.items()})
    full_url = url + (('?' + params) if params else '') + (('#' + anchor) if anchor else '')
    return dj_http.HttpResponseRedirect(full_url)


def _get_language(user: models.User, request: dj_wsgi.WSGIRequest) -> settings.i18n.Language:
    language = settings.i18n.get_language(util.get_param(request.GET, 'use_lang'))
    if not language:
        language = user.prefered_language
    return language


def _get_skin(user: models.User, request: dj_wsgi.WSGIRequest) -> str:
    skin_name = util.get_param(request.GET, 'use_skin')
    if not skin_name or not skins.get_skin(skin_name):
        skin_name = user.data.skin
    return skin_name


def _generate_js(context: page_context.PageContext) -> str:
    language = context.language
    ns_name_to_id = {}
    ns_id_to_name = {}
    talk_namespaces = []
    for ns_id, ns in settings.NAMESPACES.items():
        ns_id_to_name[str(ns_id)] = ns.get_name(local=True)
        ns_name_to_id[ns.get_name(local=False)] = ns_id
        ns_name_to_id[ns.get_name(local=True)] = ns_id
        if ns.alias:
            ns_name_to_id[ns.alias] = ns_id
        if ns.is_talk:
            talk_namespaces.append(ns_id)

    url_path = api.get_wiki_url_path()
    api_url_path = api.get_api_url_path()
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
    wpyTalkNamespaces: {talk_namespaces},
    wpyGroups: {groups},
    wpyUrlPath: "{url_path}",
    wpyApiUrlPath: "{api_url_path}",
    wpyTranslations: {json.dumps(language.javascript_mappings)}
}};
""")
