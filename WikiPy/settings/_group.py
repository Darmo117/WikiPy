"""
This module defines the UserGroup class.
"""
from __future__ import annotations

import typing as typ

from ._config_values import *
from ._i18n import Language


class UserGroup:
    def __init__(self, name: str, hide_rc: bool, needs_validation: bool, global_rights: typ.Iterable[str],
                 namespace_edit_rights: typ.Dict[int, typ.Iterable[str]], editable: bool):
        """
        This class represents a group of users.
        Different groups have different global rights and namespace-specific read/edit rights.

        :param name: This group’s name.
        :param hide_rc: If true, contributions from users belonging to this group
            will be hidden by default from recent changes.
        :param needs_validation: If true, contributions from users belonging to this group
            will have to be marked by patrollers.
        :param global_rights: Global rights for users in this group.
        :param namespace_edit_rights: Namespace read/edit rights for users in this group.
        :param editable: Indicates whether this group can be changed by a user.
        :raises ValueError: If any of the global or namespace rights is invalid.
        """
        self.__name = name
        self.__hide_rc = hide_rc
        self.__needs_validation = needs_validation
        self.__namespace_edit_rights = {}
        self.__editable = editable

        _global_rights = []
        for right in global_rights:
            if right not in GLOBAL_RIGHTS:
                raise ValueError(f'invalid value "{right}" in global rights for group "{self.__name}"')
            _global_rights.append(right)
        self.__global_rights = tuple(_global_rights)

        for ns_id, rights in namespace_edit_rights.items():
            checked_rights = []
            for right in rights:
                if right not in NAMESPACE_RIGHTS:
                    raise ValueError(
                        f'invalid value "{right}" in namespace rights for namespace {ns_id} for group "{self.__name}"')
                checked_rights.append(right)
            self.__namespace_edit_rights[ns_id] = tuple(checked_rights)

    @property
    def name(self) -> str:
        """This group’s name."""
        return self.__name

    def label(self, language: Language) -> str:
        """
        Returns this group’s label in the given language.

        :param language: The language to use.
        :return: The translated label.
        """
        return language.translate(f'group.{self.__name}')

    @property
    def editable(self) -> bool:
        """Whether this group can be modified by users."""
        return self.__editable

    @property
    def hide_from_recent_changes(self) -> bool:
        """Whether contributions from this group may be hidden from recent changes by default."""
        return self.__hide_rc

    @property
    def needs_validation(self) -> bool:
        """Whether contributions from this group need to be validated by patrollers."""
        return self.__needs_validation

    @property
    def global_rights(self) -> typ.Sequence[str]:
        """This group’s global rights."""
        return self.__global_rights

    @property
    def namespace_edit_rights(self) -> typ.Dict[int, typ.Sequence[str]]:
        """This group’s namespace read/edit rights."""
        return {k: v for k, v in self.__namespace_edit_rights.items()}

    def has_right(self, right: str) -> bool:
        """
        Checks whether this group has the specified right.

        :param right: The right to check.
        :return: True if this group has the right, false otherwise.
        """
        return right in self.__global_rights

    def can_read_pages_in_namespace(self, namespace_id: int) -> bool:
        """
        Checks whether this group can read pages in the given namespace.

        :param namespace_id: Namespace ID to check.
        :return: True if this group read pages in this namespace, false otherwise.
        """
        return RIGHT_READ_PAGES in self.__namespace_edit_rights[namespace_id]

    def can_edit_pages_in_namespace(self, namespace_id: int) -> bool:
        """
        Checks whether this group can edit pages in the given namespace.

        :param namespace_id: Namespace ID to check.
        :return: True if this group can edit pages in this namespace, false otherwise.
        """
        return RIGHT_EDIT_PAGES in self.__namespace_edit_rights[namespace_id]

    def __repr__(self):
        return f'{self.__name}[hide_rc={self.__hide_rc},global_rights={self.__global_rights},' \
               f'namespace_rights={self.__namespace_edit_rights}]'


__all__ = [
    'UserGroup',
]
