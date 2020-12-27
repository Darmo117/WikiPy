import dataclasses
import typing as typ

from . import SpecialPage, MISC_CAT
from .. import page_context, extensions as exts, parser, settings, skins as skins_, api


@dataclasses.dataclass(init=False)
class InstallInfoPageContext(page_context.PageContext):
    install_info_wikipy_version: str
    install_info_wiki_url_path: str
    install_info_api_url_path: str
    install_info_extensions: typ.List[exts.Extension]
    install_info_skins: typ.List[skins_.Skin]
    install_info_parser_functions: typ.List[parser.ParserFunction]
    install_info_parser_tags: typ.List[parser.HTMLTag]
    install_info_parser_magic_keywords: typ.List[parser.MagicKeyword]

    def __init__(
            self,
            context: page_context.PageContext,
            /,
            wikipy_version: str,
            wiki_url_path: str,
            api_url_path: str,
            skins: typ.List[skins_.Skin],
            extensions: typ.List[exts.Extension],
            parser_functions: typ.List[parser.ParserFunction],
            parser_tags: typ.List[parser.HTMLTag],
            parser_magic_keywords: typ.List[parser.MagicKeyword]
    ):
        self._context = context
        self.install_info_wiki_url_path = wiki_url_path
        self.install_info_api_url_path = api_url_path
        self.install_info_wikipy_version = wikipy_version
        self.install_info_skins = skins
        self.install_info_extensions = extensions
        self.install_info_parser_functions = parser_functions
        self.install_info_parser_tags = parser_tags
        self.install_info_parser_magic_keywords = parser_magic_keywords


class InstallInfoPage(SpecialPage):
    def __init__(self):
        super().__init__('install_info', 'Install info', category=MISC_CAT)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        context = InstallInfoPageContext(
            base_context,
            wiki_url_path=api.get_wiki_url_path(),
            api_url_path=api.get_api_url_path(),
            wikipy_version=settings.VERSION,
            skins=sorted(skins_.get_loaded_skins(), key=lambda s: s.name(base_context.language)),
            extensions=sorted(exts.get_loaded_extensions(), key=lambda e: e.name(base_context.language)),
            parser_functions=parser.WikicodeParser.registered_functions(),
            parser_tags=parser.WikicodeParser.registered_tags(),
            parser_magic_keywords=parser.WikicodeParser.registered_magic_keywords()
        )

        return context, [], None


def load_special_page() -> SpecialPage:
    return InstallInfoPage()
