import typing as typ

from . import SpecialPage


def load_special_page(settings) -> SpecialPage:
    class ContributionsPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'contributions', 'Contributions')

        def _get_data_impl(self, api, sub_title: str, request) \
                -> typ.Tuple[typ.Dict[str, typ.Any], typ.Iterable[typ.Any], typ.Optional[str]]:
            if sub_title:
                username = sub_title
                revisions = api.get_user_contributions(username)

                return {
                    'target_user_name': username,
                    'revisions': revisions,
                    'unknown_user': not api.user_exists(username),
                }, revisions, self._settings.i18n.trans('special.contributions.title_user', username=username)
            else:
                return {}, [], None

    return ContributionsPage()
