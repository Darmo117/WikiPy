import dataclasses
import typing as typ

from . import SpecialPage, get_special_pages, CATEGORIES
from .. import page_context


@dataclasses.dataclass(init=False)
class SpecialPagesPageContext(page_context.PageContext):
    special_pages: typ.Dict[str, typ.Iterable[SpecialPage]]

    def __init__(self, context: page_context.PageContext, /, special_pages: typ.Dict[str, typ.Iterable[SpecialPage]]):
        self._context = context
        self.special_pages = {ident: tuple(l) for ident, l in special_pages.items()}


class SpecialPagesPage(SpecialPage):
    def __init__(self):
        super().__init__('special_pages', 'Special pages', icon='file-cog-outline', has_css=True)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        def f(sp: SpecialPage) -> bool:
            # Filter out pages that are not categorized or the user is not allowed to access.
            return sp.category and all([
                base_context.user.has_right(right) for right in sp.requires_rights
            ])

        pages_list = sorted(filter(f, get_special_pages()), key=lambda p: p.display_title(base_context.language))
        pages = {c: [] for c in CATEGORIES}
        for page in pages_list:
            pages[page.category].append(page)
        context = SpecialPagesPageContext(base_context, special_pages=pages)

        return context, [], None


def load_special_page() -> SpecialPage:
    return SpecialPagesPage()
