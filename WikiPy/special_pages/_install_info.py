import dataclasses
import os
import typing as typ

import pkg_resources
from django.conf import settings as dj_settings

from . import SpecialPage, MISC_CAT
from .. import page_context, extensions as exts, parser, settings, skins as skins_
from ..api import titles as api_titles


@dataclasses.dataclass(init=False)
class InstallInfoPageContext(page_context.PageContext):
    install_info_wikipy_version: str
    install_info_wiki_url_path: str
    install_info_api_url_path: str
    install_info_media_backend: str
    install_info_db_manager: str
    install_info_email_backend: str
    install_info_extensions: typ.List[exts.Extension]
    install_info_skins: typ.List[skins_.Skin]
    install_info_parser_functions: typ.List[parser.ParserFunction]
    install_info_parser_tags: typ.List[parser.ExtendedHTMLTag]
    install_info_parser_magic_keywords: typ.List[parser.MagicKeyword]
    install_info_installed_packages: typ.Dict[str, str]

    def __init__(
            self,
            context: page_context.PageContext,
            /,
            wikipy_version: str,
            wiki_url_path: str,
            api_url_path: str,
            media_backend: str,
            db_manager: str,
            email_backend: str,
            skins: typ.List[skins_.Skin],
            extensions: typ.List[exts.Extension],
            parser_functions: typ.List[parser.ParserFunction],
            parser_tags: typ.List[parser.ExtendedHTMLTag],
            parser_magic_keywords: typ.List[parser.MagicKeyword],
            installed_packages: typ.Dict[str, str]
    ):
        self._context = context
        self.install_info_wiki_url_path = wiki_url_path
        self.install_info_api_url_path = api_url_path
        self.install_info_media_backend = media_backend
        self.install_info_db_manager = db_manager
        self.install_info_email_backend = email_backend
        self.install_info_wikipy_version = wikipy_version
        self.install_info_skins = skins
        self.install_info_extensions = extensions
        self.install_info_parser_functions = parser_functions
        self.install_info_parser_tags = parser_tags
        self.install_info_parser_magic_keywords = parser_magic_keywords
        self.install_info_installed_packages = installed_packages


@dataclasses.dataclass(init=False)
class InstallInfoLicensePageContext(page_context.PageContext):
    install_info_resource_name: str
    install_info_license_text: str
    install_info_resource_error: bool
    install_info_no_license: bool

    def __init__(self, context: page_context.PageContext, /, resource_name: str, license_text: str):
        self._context = context
        self.install_info_resource_name = resource_name
        self.install_info_license_text = license_text
        self.install_info_resource_error = not bool(resource_name)
        self.install_info_no_license = not bool(license_text)


class InstallInfoPage(SpecialPage):
    def __init__(self):
        super().__init__('install_info', 'Install info', category=MISC_CAT)

    def _get_data_impl(self, sub_title, base_context, request, **kwargs):
        if len(sub_title) >= 3 and sub_title[0] == 'License':
            resource_name = ''
            license_text = ''
            resource_type = sub_title[1].lower().replace(' ', '_')
            resource_id = sub_title[2].replace(' ', '_')
            resource = None

            if resource_type == 'skins':
                resource = skins_.get_skin(resource_id)
            elif resource_type == 'extensions':
                resource = exts.get_extension(resource_id)

            if resource:
                resource_name = resource.name(base_context.language)
                title = base_context.language.translate(f'special.install_info.license.{resource_type}.title',
                                                        name=resource_name)
                try:
                    with open(os.path.join(settings.WIKI_APP_DIR, resource_type, resource_id, 'LICENSE'),
                              encoding='UTF-8') as f:
                        license_text = ''.join(f.readlines())
                except FileNotFoundError:
                    pass
            else:
                title = base_context.language.translate('special.install_info.license.error.title')

            context = InstallInfoLicensePageContext(
                base_context,
                resource_name=resource_name,
                license_text=license_text
            )

        else:
            title = base_context.language.translate('special.install_info.display_title')
            installed_packages = {k: v for k, v in sorted((p.key, p.version) for p in pkg_resources.working_set)}
            context = InstallInfoPageContext(
                base_context,
                wiki_url_path=api_titles.get_wiki_url_path(),
                api_url_path=api_titles.get_api_url_path(),
                media_backend=settings.MEDIA_BACKEND_ID,
                db_manager=dj_settings.DATABASES['default']['ENGINE'],
                email_backend=dj_settings.EMAIL_BACKEND,
                wikipy_version=settings.VERSION,
                skins=sorted(skins_.get_loaded_skins(), key=lambda s: s.name(base_context.language)),
                extensions=sorted(exts.get_loaded_extensions(), key=lambda e: e.name(base_context.language)),
                parser_functions=parser.WikicodeParser.registered_functions(),
                parser_tags=parser.WikicodeParser.registered_tags(),
                parser_magic_keywords=parser.WikicodeParser.registered_magic_keywords(),
                installed_packages=installed_packages
            )

        return context, [], title


def load_special_page() -> SpecialPage:
    return InstallInfoPage()
