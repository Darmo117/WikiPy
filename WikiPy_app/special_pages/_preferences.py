import dataclasses
import typing as typ

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, api, settings


@dataclasses.dataclass(init=False)
class PreferencesPageContext(page_context.PageContext):
    prefs_edits_count: int
    prefs_form: forms.PreferencesForm
    prefs_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, edits_count: int, form: forms.PreferencesForm,
                 global_errors: typ.List[str]):
        self._context = context
        self.prefs_edits_count = edits_count
        self.prefs_form = form
        self.prefs_form_global_errors = global_errors


class PreferencesPage(SpecialPage):
    def __init__(self):
        super().__init__('preferences', 'Preferences', category=USERS_AND_RIGHTS_CAT, has_css=True, has_form=True,
                         icon='account-cog', requires_logged_in=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        errors = []

        context = base_context
        user = api.get_user_from_request(request)

        if request.method == 'POST':
            form = forms.PreferencesForm(request.POST)
            if form.is_valid():
                gender = None
                if form.cleaned_data['gender'] == 'f':
                    gender = True
                elif form.cleaned_data['gender'] == 'm':
                    gender = False
                api.update_user_data(user, **{
                    'lang_code': form.cleaned_data['prefered_language'],
                    'gender': gender,
                })
            # Reload page
            context = page_context.RedirectPageContext(base_context,
                                                       to=api.get_full_page_title(settings.SPECIAL_NS.id, self.title))

        gender = 'n'
        if user.data.is_male:
            gender = 'm'
        elif user.data.is_female:
            gender = 'f'
        form = forms.PreferencesForm(initial={
            'prefered_language': user.prefered_language.code,
            'gender': gender,
        })

        context = PreferencesPageContext(
            context,
            edits_count=len(api.get_user_contributions(user, user.username)),
            form=form,
            global_errors=errors
        )

        return context, [], None


def load_special_page() -> SpecialPage:
    return PreferencesPage()
