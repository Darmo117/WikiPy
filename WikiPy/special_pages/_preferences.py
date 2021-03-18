import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms
import django.utils.safestring as dj_safe
import pytz

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, settings, models, skins
from ..api import pages as api_pages, titles as api_titles, users as api_users


def _init_language_choices() -> typ.Iterable[typ.Tuple[str, str]]:
    choices = []

    for code, language in settings.i18n.get_languages().items():
        choices.append((code, f'{code} - {language.name}'))

    return sorted(choices)


# All in function to be able to get skins
def load_special_page() -> SpecialPage:
    class PreferencesForm(forms.WikiPyForm):
        # Personal info
        prefered_language = dj_forms.ChoiceField(
            choices=_init_language_choices(),
            label='prefered_language',
            required=True
        )
        gender = dj_forms.ChoiceField(
            choices=((g.code, g.i18n_code) for g in models.GENDERS.values()),
            label='gender',
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
        # Appearance
        skin = dj_forms.ChoiceField(
            choices=(),
            label='skin',
            widget=dj_forms.RadioSelect,
            required=True
        )
        datetime_format = dj_forms.ChoiceField(
            choices=(),
            label='datetime_format',
            widget=dj_forms.RadioSelect,
            required=True
        )
        timezone = dj_forms.ChoiceField(
            choices=(),
            label='timezone',
            required=True
        )
        max_image_preview_size = dj_forms.ChoiceField(
            choices=(),
            label='max_image_preview_size',
            required=True
        )
        max_image_thumbnail_size = dj_forms.ChoiceField(
            choices=(),
            label='max_image_thumbnail_size',
            required=True
        )
        enable_media_viewer = dj_forms.BooleanField(
            required=False,
            label='enable_media_viewer'
        )
        display_maintenance_categories = dj_forms.BooleanField(
            required=False,
            label='display_maintenance_categories'
        )
        numbered_section_titles = dj_forms.BooleanField(
            required=False,
            label='numbered_section_titles'
        )
        confirm_rollback = dj_forms.BooleanField(
            required=False,
            label='confirm_revocation'
        )
        default_revisions_list_size = dj_forms.IntegerField(
            required=True,
            label='default_revisions_list_size',
            min_value=settings.REVISIONS_LIST_PAGE_MIN,
            max_value=settings.REVISIONS_LIST_PAGE_MAX
        )
        # Editing
        all_edits_minor = dj_forms.BooleanField(
            required=False,
            label='all_edits_minor'
        )
        blank_comment_prompt = dj_forms.BooleanField(
            required=False,
            label='blank_comment_prompt'
        )
        unsaved_changes_warning = dj_forms.BooleanField(
            required=False,
            label='unsaved_changes_warning'
        )
        show_preview_first_edit = dj_forms.BooleanField(
            required=False,
            label='show_preview_first_edit'
        )
        preview_above_edit_box = dj_forms.BooleanField(
            required=False,
            label='preview_above_edit_box'
        )
        # Recent changes
        rc_max_days = dj_forms.IntegerField(
            required=True,
            label='rc_max_days',
            min_value=settings.RC_DAYS_MIN,
            max_value=settings.RC_DAYS_MAX
        )
        rc_max_revisions = dj_forms.IntegerField(
            required=True,
            label='rc_max_revisions',
            min_value=settings.RC_REVISIONS_MIN,
            max_value=settings.RC_REVISIONS_MAX
        )
        rc_group_by_page = dj_forms.BooleanField(
            required=False,
            label='rc_group_by_page'
        )
        rc_hide_minor = dj_forms.BooleanField(
            required=False,
            label='rc_hide_minor'
        )
        rc_hide_categories = dj_forms.BooleanField(
            required=False,
            label='rc_hide_categories'
        )
        rc_hide_patrolled = dj_forms.BooleanField(
            required=False,
            label='rc_hide_patrolled'
        )
        rc_hide_patrolled_new_pages = dj_forms.BooleanField(
            required=False,
            label='rc_hide_patrolled_new_pages'
        )

        def __init__(self, base_context: page_context.PageContext, *args, **kwargs):
            super().__init__('prefs', *args, warn_unsaved_changes=True, **kwargs)
            self.fields['skin'].choices = ((s.id, s.name(base_context.language)) for s in skins.get_loaded_skins())

            self.fields['datetime_format'].choices = (
                ('*', 'auto'),
                *[(i + 1, f) for i, f in enumerate(base_context.language.datetime_formats)]
            )

            zones = {}
            current_zone = ''
            for tz in sorted(pytz.common_timezones):
                zone, *rest = tz.split('/')
                rest = '/'.join(rest)
                is_international = not rest
                if is_international:
                    rest = zone
                    zone = 'International'

                if zone != current_zone:
                    current_zone = base_context.language.translate('timezone.' + zone + '.label')
                    if current_zone not in zones:
                        zones[current_zone] = []

                tz_label = base_context.language.translate('timezone.' + zone + '.timezones.' + rest,
                                                           none_if_undefined=True) or rest
                if not is_international:
                    tz_label = current_zone + '/' + tz_label

                zones[current_zone].append((tz, tz_label))

            choices = [(k, sorted(v, key=lambda e: e[1])) for k, v in zones.items()]
            choices.sort(key=lambda e: e[0])
            self.fields['timezone'].choices = choices

            self.fields['max_image_preview_size'].choices = (
                (s, f'{s}\u00a0px') for s in settings.IMAGE_PREVIEW_SIZES
            )

            self.fields['max_image_thumbnail_size'].choices = (
                (s, f'{s}\u00a0px') for s in settings.THUMBNAIL_SIZES
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
            user = api_users.get_user_from_request(request)
            groups = list(map(lambda group: group.label(base_context.language), user.groups))
            groups.sort()
            edits_count = len(api_users.get_user_contributions(user, user.username))
            rendered_signature = dj_safe.mark_safe(
                api_pages.render_wikicode(user.data.signature, base_context, no_redirect=True)[0])

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
                'timezone': user.data.timezone,
                'max_image_preview_size': user.data.max_image_file_preview_size,
                'max_image_thumbnail_size': user.data.max_image_thumbnail_size,
                'enable_media_viewer': user.data.enable_media_viewer,
                'display_maintenance_categories': user.data.display_maintenance_categories,
                'numbered_section_titles': user.data.numbered_section_titles,
                'confirm_rollback': user.data.confirm_rollback,

                'default_revisions_list_size': user.data.default_revisions_list_size,
                'all_edits_minor': user.data.all_edits_minor,
                'blank_comment_prompt': user.data.blank_comment_prompt,
                'unsaved_changes_warning': user.data.unsaved_changes_warning,
                'show_preview_first_edit': user.data.show_preview_first_edit,
                'preview_above_edit_box': user.data.preview_above_edit_box,

                'rc_max_days': user.data.rc_max_days,
                'rc_max_revisions': user.data.rc_max_revisions,
                'rc_group_by_page': user.data.rc_group_by_page,
                'rc_hide_minor': user.data.rc_hide_minor,
                'rc_hide_categories': user.data.rc_hide_categories,
                'rc_hide_patrolled': user.data.rc_hide_patrolled,
                'rc_hide_patrolled_new_pages': user.data.rc_hide_patrolled_new_pages,
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
                api_users.update_user_data(
                    user,

                    lang_code=form.cleaned_data['prefered_language'],
                    gender=models.GENDERS[form.cleaned_data['gender']],
                    signature=form.cleaned_data['signature'],
                    users_can_send_emails=form.cleaned_data['users_can_send_emails'],
                    send_copy_of_sent_emails=form.cleaned_data['send_copy_of_sent_emails'],
                    send_watchlist_emails=form.cleaned_data['send_watchlist_emails'],
                    send_minor_watchlist_emails=form.cleaned_data['send_minor_watchlist_emails'],

                    datetime_format_id=int(datetime_format) if datetime_format != '*' else None,
                    timezone=form.cleaned_data['timezone'],
                    max_image_file_preview_size=int(form.cleaned_data['max_image_preview_size']),
                    max_image_thumbnail_size=int(form.cleaned_data['max_image_thumbnail_size']),
                    enable_media_viewer=form.cleaned_data['enable_media_viewer'],
                    display_maintenance_categories=form.cleaned_data['display_maintenance_categories'],
                    numbered_section_titles=form.cleaned_data['numbered_section_titles'],
                    confirm_rollback=form.cleaned_data['confirm_rollback'],

                    default_revisions_list_size=form.cleaned_data['default_revisions_list_size'],
                    all_edits_minor=form.cleaned_data['all_edits_minor'],
                    blank_comment_prompt=form.cleaned_data['blank_comment_prompt'],
                    unsaved_changes_warning=form.cleaned_data['unsaved_changes_warning'],
                    show_preview_first_edit=form.cleaned_data['show_preview_first_edit'],
                    preview_above_edit_box=form.cleaned_data['preview_above_edit_box'],

                    rc_max_days=form.cleaned_data['rc_max_days'],
                    rc_max_revisions=form.cleaned_data['rc_max_revisions'],
                    rc_group_by_page=form.cleaned_data['rc_group_by_page'],
                    rc_hide_minor=form.cleaned_data['rc_hide_minor'],
                    rc_hide_categories=form.cleaned_data['rc_hide_categories'],
                    rc_hide_patrolled=form.cleaned_data['rc_hide_patrolled'],
                    rc_hide_patrolled_new_pages=form.cleaned_data['rc_hide_patrolled_new_pages']
                )
                # Reload page
                return page_context.RedirectPageContext(
                    base_context,
                    to=api_titles.get_full_page_title(settings.SPECIAL_NS.id, self.title)
                )
            return PreferencesPageContext(
                base_context,
                groups=groups,
                edits_count=edits_count,
                rendered_signature=rendered_signature,
                form=form,
                global_errors=errors
            )

    return PreferencesPage()
