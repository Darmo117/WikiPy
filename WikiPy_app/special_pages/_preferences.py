import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms
import django.utils.safestring as dj_safe

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, api, settings, models, skins


def _init_language_choices() -> typ.Iterable[typ.Tuple[str, str]]:
    choices = []

    for code, language in settings.i18n.get_languages().items():
        choices.append((code, f'{code} - {language.name}'))

    return sorted(choices)


# All in function to be able to get skins
def load_special_page() -> SpecialPage:
    class PreferencesForm(forms.WikiPyForm):
        prefered_language = dj_forms.ChoiceField(
            choices=_init_language_choices(),
            label='prefered_language',
            required=True
        )
        gender = dj_forms.ChoiceField(
            choices=((g.code, g.i18n_code) for g in models.GENDERS.values()),
            widget=dj_forms.RadioSelect,
            required=True
        )
        signature = dj_forms.CharField(
            max_length=models.UserData._meta.get_field('signature').max_length,
            label='signature',
            required=True
        )
        users_can_send_emails = dj_forms.BooleanField(
            label='users_can_send_emails',
            required=False
        )
        send_copy_of_sent_emails = dj_forms.BooleanField(
            label='send_copy_of_sent_emails',
            required=False
        )
        send_watchlist_emails = dj_forms.BooleanField(
            label='send_watchlist_emails',
            required=False
        )
        send_minor_watchlist_emails = dj_forms.BooleanField(
            label='send_minor_watchlist_emails',
            required=False
        )
        users_email_blacklist = dj_forms.CharField(
            label='users_email_blacklist',
            required=False
        )
        skin = dj_forms.ChoiceField(
            choices=((s.name, s.label) for s in skins.get_loaded_skins()),
            widget=dj_forms.RadioSelect,
            required=True
        )
        datetime_format = dj_forms.ChoiceField(
            choices=(),
            widget=dj_forms.RadioSelect,
            required=True
        )

        def __init__(self, base_context: page_context.PageContext, *args, **kwargs):
            super().__init__('prefs', *args, **kwargs)
            self.fields['datetime_format'].choices = (
                ('*', 'auto'),
                *[(i + 1, f) for i, f in enumerate(base_context.language.datetime_formats)]
            )

    @dataclasses.dataclass(init=False)
    class PreferencesPageContext(page_context.PageContext):
        prefs_groups: typ.List[str]
        prefs_edits_count: int
        prefs_rendered_signature: str
        prefs_form: PreferencesForm
        prefs_form_global_errors: typ.List[str]

        def __init__(self, context: page_context.PageContext, /, groups: typ.List[str], edits_count: int,
                     rendered_signature: str, form: PreferencesForm, global_errors: typ.List[str] = None):
            self._context = context
            self.prefs_groups = groups
            self.prefs_edits_count = edits_count
            self.prefs_rendered_signature = rendered_signature
            self.prefs_form = form
            self.prefs_form_global_errors = global_errors

    class PreferencesPage(SpecialPage):
        def __init__(self):
            super().__init__('preferences', 'Preferences', category=USERS_AND_RIGHTS_CAT, has_css=True, has_js=True,
                             has_form=True, icon='account-cog', requires_logged_in=True)

        def _get_data_impl(self, sub_title, base_context, request, **kwargs):
            user = api.get_user_from_request(request)
            groups = list(map(lambda group: group.label(base_context.language), user.groups))
            groups.sort()
            edits_count = len(api.get_user_contributions(user, user.username))
            rendered_signature = dj_safe.mark_safe(
                api.render_wikicode(user.data.signature, base_context, no_redirect=True)[0])

            if request.method == 'POST':
                context = self.__save_preferences(base_context, user, groups, edits_count, rendered_signature, request)
            else:
                context = self.__get_default_context(base_context, user, groups, edits_count, rendered_signature)

            return context, [], None

        # noinspection PyMethodMayBeStatic
        def __get_default_context(self, base_context: page_context.PageContext, user: models.User,
                                  groups: typ.List[str],
                                  edits_count: int, rendered_signature: str) \
                -> page_context.PageContext:
            if user.data.datetime_format_id:
                datetime_format = str(user.data.datetime_format_id % len(base_context.language.datetime_formats))
            else:
                datetime_format = '*'
            form = PreferencesForm(base_context, initial={
                'prefered_language': user.prefered_language.code,
                'gender': user.data.gender.code,
                'signature': user.data.signature,
                'users_can_send_emails': user.data.users_can_send_emails,
                'send_copy_of_sent_emails': user.data.send_copy_of_sent_emails,
                'send_watchlist_emails': user.data.send_watchlist_emails,
                'send_minor_watchlist_emails': user.data.send_minor_watchlist_emails,
                'skin': user.data.skin,
                'datetime_format': datetime_format,
            })

            return PreferencesPageContext(
                base_context,
                groups=groups,
                edits_count=edits_count,
                rendered_signature=rendered_signature,
                form=form
            )

        def __save_preferences(self, base_context: page_context.PageContext, user: models.User, groups: typ.List[str],
                               edits_count: int, rendered_signature: str, request: dj_wsgi.WSGIRequest):
            errors = []
            form = PreferencesForm(base_context, request.POST)
            if form.is_valid():
                datetime_format = form.cleaned_data['datetime_format']
                api.update_user_data(
                    user,
                    lang_code=form.cleaned_data['prefered_language'],
                    gender=models.GENDERS[form.cleaned_data['gender']],
                    signature=form.cleaned_data['signature'],
                    users_can_send_emails=form.cleaned_data['users_can_send_emails'],
                    send_copy_of_sent_emails=form.cleaned_data['send_copy_of_sent_emails'],
                    send_watchlist_emails=form.cleaned_data['send_watchlist_emails'],
                    send_minor_watchlist_emails=form.cleaned_data['send_minor_watchlist_emails'],
                    datetime_format_id=datetime_format if datetime_format != '*' else None
                )
                # Reload page
                return page_context.RedirectPageContext(base_context,
                                                        to=api.get_full_page_title(settings.SPECIAL_NS.id, self.title))
            return PreferencesPageContext(
                base_context,
                groups=groups,
                edits_count=edits_count,
                rendered_signature=rendered_signature,
                form=form,
                global_errors=errors
            )

    return PreferencesPage()
