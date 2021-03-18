import dataclasses
import typing as typ

import django.forms as dj_forms

from . import SpecialPage, LOGS_CAT
from .. import page_context, forms, settings
from ..api import titles as api_titles, logs as api_logs


def get_log_ids():
    return ['all', *api_logs.get_log_ids()]


class LogsForm(forms.WikiPyForm):
    type = dj_forms.ChoiceField(
        choices=(),
        label='type',
        required=True
    )
    performer = dj_forms.CharField(
        max_length=200,
        label='performer',
        required=False,
    )
    target = dj_forms.CharField(
        max_length=200,
        label='target',
        required=False,
    )
    from_date = dj_forms.DateField(
        label='from_date',
        widget=dj_forms.TextInput(attrs={'type': 'date'}),
        required=False
    )
    to_date = dj_forms.DateField(
        label='to_date',
        widget=dj_forms.TextInput(attrs={'type': 'date'}),
        required=False
    )

    def __init__(self, context, *args, **kwargs):
        super().__init__('logs', *args, **kwargs)
        self.fields['type'].choices = sorted([
            (log, context.language.translate(f'log.{log}.title')) for log in get_log_ids()
        ], key=lambda e: e[1] if e[0] != 'all' else '')


@dataclasses.dataclass(init=False)
class LogsPageContext(page_context.PageContext):
    logs_form: LogsForm
    logs_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, form: LogsForm, global_errors: typ.List[str]):
        self._context = context
        self.logs_form = form
        self.logs_form_global_errors = global_errors


class LogsPage(SpecialPage):
    def __init__(self):
        super().__init__('logs', 'Logs', category=LOGS_CAT, icon='notebook-outline', access_key='j', has_js=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        page_title = api_titles.get_actual_page_title('/'.join(sub_title)) if sub_title else None

        form = LogsForm(base_context, request.GET)
        if form.is_valid():
            log_id = form.cleaned_data['type']
            performer = form.cleaned_data['performer']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            target = form.cleaned_data['target'] or page_title
        else:
            # TODO all
            log_id = 'all'
            performer = None
            from_date = None
            to_date = None
            target = page_title

        form_data = {
            'type': log_id,
            'performer': performer,
            'from_date': from_date,
            'to_date': to_date,
            'target': target,
        }

        if log_id:
            title = base_context.language.translate(f'log.{log_id}.title')
        else:
            title = base_context.language.translate('log.all')

        if page_title:  # Redirect to page without subtitle
            url = (api_titles.get_wiki_url_path()
                   + api_titles.get_full_page_title(settings.SPECIAL_NS.id, self.get_title())
                   + '?' + '&'.join([f'{k}={v}' for k, v in form_data.items() if v]))
            return page_context.RedirectPageContext(base_context, to=url, is_path=True), [], title

        entries = api_logs.get_log_entries(log_id, performer, from_date, to_date, target)

        form = LogsForm(base_context, initial=form_data)
        context = LogsPageContext(base_context, form, [])

        return context, entries, title


def load_special_page() -> SpecialPage:
    return LogsPage()
