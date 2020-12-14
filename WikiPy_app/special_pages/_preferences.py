import dataclasses
import typing as typ

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, api, util


@dataclasses.dataclass(init=False)
class PreferencesPageContext(page_context.PageContext):
    prefs_form: forms.PreferencesForm
    prefs_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, form: forms.PreferencesForm,
                 global_errors: typ.List[str]):
        self._context = context
        self.prefs_form = form
        self.prefs_form_global_errors = global_errors


class PreferencesPage(SpecialPage):
    def __init__(self):
        super().__init__('preferences', 'Preferences', category=USERS_AND_RIGHTS_CAT, has_js=True, has_form=True,
                         icon='account-cog')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        errors = []

        if request.method == 'POST':
            user = api.get_user_from_request(request)
            form = forms.PreferencesForm(request.POST)
            if form.is_valid():
                user.data.lang_code = form.cleaned_data['prefered_language']
                user.data.save()
        else:
            user = base_context.user
            form = forms.PreferencesForm(
                initial={
                    'prefered_language': user.prefered_language.code
                }
            )

        context = PreferencesPageContext(
            base_context,
            form=form,
            global_errors=errors
        )

        return context, [], None


def load_special_page() -> SpecialPage:
    return PreferencesPage()
