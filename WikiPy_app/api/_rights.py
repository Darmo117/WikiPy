from __future__ import annotations

import typing as typ
from .. import settings

_GROUPS = {}


def get_groups() -> typ.Dict[int, UserGroup]:
    return _GROUPS


def get_group_for_id(group_id: int) -> typ.Optional[int]:
    return _GROUPS[group_id] if group_id in _GROUPS else None


class UserGroup:
    def __init__(self, name: str, namespace_edit_rights: typ.Dict[int, typ.List[str]], *rights: str):
        self.__name = name
        self.__label = settings.l10n.USER_GROUPS_NAMES[name]
        self.__namespace_edit_rights = namespace_edit_rights
        self.__rights = rights

    @property
    def name(self) -> str:
        return self.__name

    @property
    def label(self):
        return self.__label

    def can_edit_page(self, page) -> bool:
        """
        Checks whether this group can edit the given page.

        :param page: The page.
        :type page: django_wiki.models.Page
        :return: True if this group can edit the given page.
        """
        return self.__check_page_right(page, settings.RIGHT_EDIT_PAGE)

    def can_delete_page(self, page) -> bool:
        """
        Checks whether this group can delete the given page.

        :param page: The page.
        :type page: django_wiki.models.Page
        :return: True if this group can delete the given page.
        """
        return self.__check_page_right(page, settings.RIGHT_DELETE_PAGE)

    def can_rename_page(self, page) -> bool:
        """
        Checks whether this group can rename the given page.

        :param page: The page.
        :type page: django_wiki.models.Page
        :return: True if this group can rename the given page.
        """
        return self.__check_page_right(page, settings.RIGHT_RENAME_PAGE)

    def can_hide_revisions(self) -> bool:
        """Checks whether this group can hide page revisions."""
        return settings.RIGHT_HIDE_REVISION in self.__rights

    def can_protect_pages(self) -> bool:
        """Checks whether this group can protect pages."""
        return settings.RIGHT_PROTECT_PAGES in self.__rights

    def can_rename_users(self) -> bool:
        """Checks whether this group can rename users."""
        return settings.RIGHT_RENAME_USERS in self.__rights

    def can_edit_users_groups(self) -> bool:
        """Checks whether this group can edit users’s groups."""
        return settings.RIGHT_EDIT_USERS_GROUPS in self.__rights

    def can_ban_users(self) -> bool:
        """Checks whether this group can ban users."""
        return settings.RIGHT_BAN_USERS in self.__rights

    def __check_page_right(self, page, right: str) -> bool:
        ns_id = page.namespace_id

        ns_ok = right in self.__namespace_edit_rights[ns_id]

        # TODO vérifier le niveau de protection

        return ns_ok


def _add_group(group: UserGroup):
    _GROUPS[group.name] = group


def _init():
    for group, rights in settings.EDIT_RIGHTS.items():
        if settings.ACCOUNT_REQUIRED and group == 'anonymous':
            ns_rights = []
        else:
            ns_rights = rights['namespaces']
        _add_group(UserGroup(group, ns_rights, *rights['other']))


_init()
