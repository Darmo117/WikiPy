import dataclasses
import datetime as dt

from . import SpecialPage
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class ContributionsPageContext(page_context.PageContext):
        contribs_target_username: str
        contribs_unknown_user: bool
        contribs_results_found: bool
        contribs_form_namespace: int
        contribs_form_only_hidden_revisions: bool
        contribs_form_only_last_edits: bool
        contribs_form_only_page_creations: bool
        contribs_form_hide_minor: bool
        contribs_form_from_date: str
        contribs_form_to_date: str

        def __init__(self, context: page_context.PageContext, /, contribs_target_username: str,
                     contribs_unknown_user: bool, contribs_results_found: bool, contribs_form_namespace: int = None,
                     contribs_form_only_hidden_revisions: bool = False, contribs_form_only_last_edits: bool = False,
                     contribs_form_only_page_creations: bool = False, contribs_form_hide_minor: bool = False,
                     contribs_form_from_date: dt.date = None, contribs_form_to_date: dt.date = None):
            self._context = context
            self.contribs_target_username = contribs_target_username
            self.contribs_unknown_user = contribs_unknown_user
            self.contribs_results_found = contribs_results_found
            self.contribs_form_namespace = contribs_form_namespace
            self.contribs_form_only_hidden_revisions = contribs_form_only_hidden_revisions
            self.contribs_form_only_last_edits = contribs_form_only_last_edits
            self.contribs_form_only_page_creations = contribs_form_only_page_creations
            self.contribs_form_hide_minor = contribs_form_hide_minor
            self.contribs_form_from_date = contribs_form_from_date.isoformat() if contribs_form_from_date else None
            self.contribs_form_to_date = contribs_form_to_date.isoformat() if contribs_form_to_date else None

    class ContributionsPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'contributions', 'Contributions', has_js=True)

        def _get_data_impl(self, api, sub_title, base_context, request, **kwargs):
            if len(sub_title) != 0:
                user = api.get_user_from_request(request)
                username = sub_title[0]
                namespace = api.get_param(request.GET, 'namespace', expected_type=int)
                only_hidden_revisions = api.get_param(request.GET, 'only_hidden_revisions', expected_type=int)
                only_last_edits = api.get_param(request.GET, 'only_last_edits', expected_type=bool)
                only_page_creations = api.get_param(request.GET, 'only_page_creations', expected_type=bool)
                hide_minor = api.get_param(request.GET, 'hide_minor', expected_type=bool)
                from_date = api.get_param(request.GET, 'from', expected_type=dt.date.fromisoformat)
                to_date = api.get_param(request.GET, 'to', expected_type=dt.date.fromisoformat)
                args = {
                    'namespace': namespace,
                    'only_hidden_revisions': only_hidden_revisions,
                    'only_last_edits': only_last_edits,
                    'only_page_creations': only_page_creations,
                    'hide_minor': hide_minor,
                    'from_date': from_date,
                    'to_date': to_date,
                }
                revisions = api.get_user_contributions(user, username, **args)
                title = self._settings.i18n.trans('special.contributions.title_user', username=username)
            else:
                username = None
                revisions = []
                title = None
                args = {}

            context = ContributionsPageContext(
                base_context,
                contribs_target_username=username,
                contribs_unknown_user=not api.user_exists(username),
                contribs_results_found=len(revisions) != 0,
                **{('contribs_form_' + k): v for k, v in args.items()}
            )

            return context, revisions, title

    return ContributionsPage()
