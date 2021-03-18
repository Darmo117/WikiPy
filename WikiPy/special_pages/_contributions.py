import dataclasses
import typing as typ

import django.forms as dj_forms

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, util
from ..api import users as api_users


class ContributionsForm(forms.WikiPyForm):
    target_user = dj_forms.CharField(
        label='target_user',
        required=True,
        validators=[api_users.log_in_username_validator]
    )
    namespace = dj_forms.ChoiceField(
        choices=(),
        label='namespace',
        required=False
    )
    from_date = dj_forms.DateField(
        label='from',
        required=False,
        widget=dj_forms.TextInput(attrs={'type': 'date'})
    )
    to_date = dj_forms.DateField(
        label='to',
        required=False,
        widget=dj_forms.TextInput(attrs={'type': 'date'})
    )
    only_hidden_revisions = dj_forms.BooleanField(
        label='only_hidden_revisions',
        required=False
    )
    only_last_edits = dj_forms.BooleanField(
        label='only_last_edits',
        required=False
    )
    only_page_creations = dj_forms.BooleanField(
        label='only_page_creations',
        required=False
    )
    hide_minor = dj_forms.BooleanField(
        label='hide_minor',
        required=False
    )

    def __init__(self, base_context, *args, **kwargs):
        super().__init__('contribs', *args, **kwargs)
        self.fields['namespace'].choices = forms.init_namespace_choices(add_all=True, language=base_context.language)


@dataclasses.dataclass(init=False)
class ContributionsPageContext(page_context.PageContext):
    contribs_target_username: str
    contribs_results_found: bool
    contribs_form: ContributionsForm
    contribs_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, contribs_target_username: str,
                 contribs_results_found: bool, form: ContributionsForm, global_errors: typ.List[str]):
        self._context = context
        self.contribs_target_username = contribs_target_username
        self.contribs_results_found = contribs_results_found
        self.contribs_form = form
        self.contribs_form_global_errors = global_errors


class ContributionsPage(SpecialPage):
    def __init__(self):
        super().__init__('contributions', 'Contributions', category=USERS_AND_RIGHTS_CAT, has_js=True, has_form=True,
                         icon='puzzle', access_key='c')

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        username = None
        revisions = []
        title = None
        errors = []

        if len(sub_title) != 0:
            user = api_users.get_user_from_request(request)
            form = ContributionsForm(base_context, util.add_entries(request.GET, target_user=sub_title[0]))
            if form.is_valid():
                username = form.cleaned_data['target_user']
                namespace = form.cleaned_data['namespace']
                args = {
                    'namespace': int(namespace) if namespace != '' else None,
                    'only_hidden_revisions': form.cleaned_data['only_hidden_revisions'],
                    'only_last_edits': form.cleaned_data['only_last_edits'],
                    'only_page_creations': form.cleaned_data['only_page_creations'],
                    'hide_minor': form.cleaned_data['hide_minor'],
                    'from_date': form.cleaned_data['from_date'],
                    'to_date': form.cleaned_data['to_date'],
                }
                revisions = api_users.get_user_contributions(user, username, **args)
                title = base_context.language.translate('special.contributions.title_user', username=username)
        else:
            form = ContributionsForm(base_context)

        context = ContributionsPageContext(
            base_context,
            contribs_target_username=username,
            contribs_results_found=len(revisions) != 0,
            form=form,
            global_errors=errors
        )

        return context, revisions, title


def load_special_page() -> SpecialPage:
    return ContributionsPage()
