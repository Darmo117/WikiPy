import dataclasses
import datetime
import typing as typ

import dateutil.relativedelta as du_delta
import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings, forms
from ..api import pages as api_pages, titles as api_titles, errors as api_errors, datetime as api_dt


class ProtectPageForm(forms.WikiPyForm):
    namespace = dj_forms.ChoiceField(
        choices=(),
        label='namespace',
        required=False
    )
    title = dj_forms.CharField(
        max_length=100,
        label='title',
        validators=[api_pages.page_title_validator],
        required=True,
        help_text=True
    )
    level = dj_forms.ChoiceField(
        choices=(),
        label='level',
        required=True
    )
    # Not used for validation, only for JavaScript
    predefined_expiration_date = dj_forms.ChoiceField(
        choices=(),
        label='predefined_expiration_date',
        required=False,
        help_text=True
    )
    expiration_date = dj_forms.DateField(
        label='expiration_date',
        widget=dj_forms.TextInput(attrs={'type': 'date'}),
        required=False,
        help_text=True
    )
    reason = dj_forms.CharField(
        max_length=200,
        label='reason',
        required=True,
        help_text=True
    )
    apply_to_talk = dj_forms.BooleanField(
        label='apply_to_talk',
        required=False
    )
    apply_to_subpages = dj_forms.BooleanField(
        label='apply_to_subpages',
        required=False
    )

    def __init__(self, base_context, *args, **kwargs):
        """

        :param base_context:
        :type base_context: WikiPy.page_context.PageContext
        :param args:
        :param kwargs:
        """
        super().__init__('protect_page', *args, **kwargs)
        self.fields['namespace'].choices = forms.init_namespace_choices(add_all=False, language=base_context.language)
        self.fields['level'].choices = sorted(
            ((g_id, g.label(base_context.language)) for g_id, g in settings.GROUPS.items()),
            key=lambda e: e[1] if e[0] != 'all' else ''
        )
        now = api_dt.now().date()
        deltas = (
            (1, 'days'),
            (1, 'weeks'),
            (2, 'weeks'),
            (1, 'months'),
            (3, 'months'),
            (6, 'months'),
            (1, 'years'),
        )
        label_c = base_context.language.translate('special.protect_page.form.predefined_expiration_date.custom_date')
        label_i = base_context.language.translate('special.protect_page.form.predefined_expiration_date.infinite')
        self.fields['predefined_expiration_date'].choices = (('other', label_c),) + tuple(
            (now + du_delta.relativedelta(**{unit: duration}),
             base_context.language.translate(f'duration.{unit}', duration=duration, plural_number=duration))
            for duration, unit in deltas
        ) + (('', label_i),)


@dataclasses.dataclass(init=False)
class ProtectPageContext(page_context.PageContext):
    protect_page_form: ProtectPageForm
    protect_page_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, form: ProtectPageForm, global_errors: typ.List[str]):
        self._context = context
        self.protect_page_form = form
        self.protect_page_form_global_errors = global_errors


class ProtectPage(SpecialPage):
    def __init__(self):
        super().__init__('protect_page', 'Protect page', category=PAGE_TOOLS_CAT, icon='shield-edit', access_key='=',
                         requires_rights=(settings.RIGHT_PROTECT_PAGES,), has_js=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        page_title = api_titles.get_actual_page_title('/'.join(sub_title)) if sub_title else ''
        if request.method == 'POST':
            context = self.__protect(base_context, request)
        else:
            context = self.__get_default_context(base_context, page_title)

        if page_title:
            title = context.language.translate('special.protect_page.title_page', page_title=page_title)
        else:
            title = context.language.translate('special.protect_page.title_no_page')

        return context, [], title

    # noinspection PyMethodMayBeStatic
    def __get_default_context(self, base_context: page_context.PageContext, sub_title: str) -> page_context.PageContext:
        ns_id, title = api_titles.extract_namespace_and_title(sub_title, ns_as_id=True)
        res = api_pages.get_page_protection(ns_id, title)
        if res:
            prot = res[0]
            level = prot.protection_level
            exp_date = prot.expiration_date
            apply_to_talk = prot.applies_to_talk_page
        else:
            level = None
            exp_date = None
            apply_to_talk = False

        return ProtectPageContext(
            base_context,
            form=ProtectPageForm(base_context, initial={
                'namespace': ns_id,
                'title': title,
                'level': level,
                'predefined_expiration_date': '' if exp_date is None else 'other',
                'expiration_date': exp_date,
                'apply_to_talk': apply_to_talk,
            }),
            global_errors=[]
        )

    # noinspection PyMethodMayBeStatic
    def __protect(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest) \
            -> page_context.PageContext:
        errors = []
        form = ProtectPageForm(base_context, request.POST)

        if form.is_valid():
            namespace_id = int(form.cleaned_data['namespace'])
            title = form.cleaned_data['title']
            protection_level = form.cleaned_data['level']
            reason = form.cleaned_data['reason']
            apply_to_talk = form.cleaned_data['apply_to_talk']
            apply_to_subpages = form.cleaned_data['apply_to_subpages']
            pred_exp_date = form.cleaned_data['predefined_expiration_date']
            if pred_exp_date == 'other':
                exp_date = form.cleaned_data['expiration_date']
            elif pred_exp_date == '':
                exp_date = None
            else:
                exp_date = datetime.date.fromisoformat(pred_exp_date)
            try:
                api_pages.protect_page(namespace_id, title, protection_level, reason, apply_to_talk,
                                       apply_to_subpages, exp_date, performer=base_context.user)
            except (api_errors.PageProtectionForbiddenError, api_errors.MissingRightError):
                errors.append('protect_forbidden')
            else:
                # Redirect to origin page
                return page_context.RedirectPageContext(
                    base_context,
                    to=api_titles.get_full_page_title(namespace_id, title)
                )

        return ProtectPageContext(
            base_context,
            form=form,
            global_errors=errors
        )


def load_special_page() -> SpecialPage:
    return ProtectPage()
