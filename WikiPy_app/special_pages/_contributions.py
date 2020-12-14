import dataclasses
import typing as typ

from . import SpecialPage, USERS_AND_RIGHTS_CAT
from .. import page_context, forms, api, util


@dataclasses.dataclass(init=False)
class ContributionsPageContext(page_context.PageContext):
    contribs_target_username: str
    contribs_results_found: bool
    contribs_form: forms.ContributionsForm
    contribs_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, contribs_target_username: str,
                 contribs_results_found: bool, form: forms.ContributionsForm, global_errors: typ.List[str]):
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
            user = api.get_user_from_request(request)
            form = forms.ContributionsForm(util.add_entries(request.GET, target_user=sub_title[0]))
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
                revisions = api.get_user_contributions(user, username, **args)
                title = base_context.language.translate('special.contributions.title_user', username=username)
        else:
            form = forms.ContributionsForm()

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
