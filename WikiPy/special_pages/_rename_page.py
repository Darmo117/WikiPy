import dataclasses
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.forms as dj_forms

from . import SpecialPage, PAGE_TOOLS_CAT
from .. import page_context, settings, forms
from ..api import pages as api_pages, titles as api_titles, errors as api_errors


class RenamePageForm(forms.WikiPyForm):
    current_namespace = dj_forms.ChoiceField(
        choices=(),
        label='current_namespace',
        required=False
    )
    current_title = dj_forms.CharField(
        max_length=100,
        label='current_title',
        validators=[api_pages.page_title_validator],
        required=True,
        help_text=True
    )
    new_namespace = dj_forms.ChoiceField(
        choices=(),
        label='new_namespace',
        required=False
    )
    new_title = dj_forms.CharField(
        max_length=100,
        label='new_title',
        validators=[api_pages.page_title_validator],
        required=True,
        help_text=True
    )
    reason = dj_forms.CharField(
        max_length=200,
        label='reason',
        required=True,
        help_text=True
    )
    create_redirection = dj_forms.BooleanField(
        label='create_redirection',
        required=False
    )

    def __init__(self, base_context, *args, **kwargs):
        super().__init__('rename_page', *args, **kwargs)
        self.fields['current_namespace'].choices = forms.init_namespace_choices(add_all=False,
                                                                                language=base_context.language)
        self.fields['new_namespace'].choices = forms.init_namespace_choices(add_all=False,
                                                                            language=base_context.language)
        self.fields['create_redirection'].disabled = not base_context.user.has_right(settings.RIGHT_DELETE_PAGES)


@dataclasses.dataclass(init=False)
class RenamePageContext(page_context.PageContext):
    rename_page_form: RenamePageForm
    rename_page_form_global_errors: typ.List[str]

    def __init__(self, context: page_context.PageContext, /, form: RenamePageForm, global_errors: typ.List[str]):
        self._context = context
        self.rename_page_form = form
        self.rename_page_form_global_errors = global_errors


class RenamePage(SpecialPage):
    def __init__(self):
        super().__init__('rename_page', 'Rename page', category=PAGE_TOOLS_CAT, icon='rename-box', access_key='r',
                         requires_rights=(settings.RIGHT_RENAME_PAGES,))

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        page_title = api_titles.get_actual_page_title('/'.join(sub_title)) if sub_title else ''
        if request.method == 'POST':
            context = self.__rename(base_context, request)
        else:
            context = self.__get_default_context(base_context, page_title)

        if page_title:
            title = context.language.translate('special.rename_page.title_page', page_title=page_title)
        else:
            title = context.language.translate('special.rename_page.title_no_page')

        return context, [], title

    # noinspection PyMethodMayBeStatic
    def __get_default_context(self, base_context: page_context.PageContext, sub_title: str) -> page_context.PageContext:
        ns_id, title = api_titles.extract_namespace_and_title(sub_title, ns_as_id=True)

        return RenamePageContext(
            base_context,
            form=RenamePageForm(base_context, initial={
                'current_namespace': ns_id,
                'current_title': title,
                'new_namespace': ns_id,
                'new_title': title,
                'create_redirection': not base_context.user.has_right(settings.RIGHT_DELETE_PAGES),
            }),
            global_errors=[]
        )

    # noinspection PyMethodMayBeStatic
    def __rename(self, base_context: page_context.PageContext, request: dj_wsgi.WSGIRequest) \
            -> page_context.PageContext:
        errors = []
        form = RenamePageForm(base_context, request.POST)

        if form.is_valid():
            current_namespace_id = int(form.cleaned_data['current_namespace'])
            current_title = form.cleaned_data['current_title']
            new_namespace_id = int(form.cleaned_data['new_namespace'])
            new_title = form.cleaned_data['new_title']
            reason = form.cleaned_data['reason']
            create_redirection = form.cleaned_data['create_redirection']
            try:
                api_pages.rename_page(base_context, current_namespace_id, current_title, new_namespace_id, new_title,
                                      reason, create_redirection, performer=base_context.user)
            except api_errors.PageRenameForbiddenError as e:
                errors.append(
                    {
                        'origin page does not exist': 'origin_page_does_not_exist',
                        'target page already exists': 'target_page_already_exists',
                        'rename forbidden': 'cannot_rename',
                        'target edit forbidden': 'cannot_edit_target_page',
                        'same origin and target titles': 'same_old_and_new_titles',
                    }.get(e.code)
                )
            except api_errors.PageEditConflictError as e:
                pass  # TODO
            except api_errors.PageEditForbiddenError as e:
                pass  # TODO
            except api_errors.MissingRightError as e:
                pass  # TODO
            else:
                # TODO Redirect to action summary page
                pass

        return RenamePageContext(
            base_context,
            form=form,
            global_errors=errors
        )


def load_special_page() -> SpecialPage:
    return RenamePage()
