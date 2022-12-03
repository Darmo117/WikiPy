"""
This module defines the UserGroup class.
"""
from __future__ import annotations

import typing as typ

from ._config_values import *
from ._i18n import Language


class UserGroup:
    def __init__(self, name: str, rights: typ.Iterable[str], editable: bool):
        """
        This class represents a group of users.
        Different groups have different global rights and namespace-specific read/edit rights.

        :param name: This group’s name.
        :param rights: Global rights for users in this group.
        :param editable: Indicates whether this group can be changed by a user.
        :raises ValueError: If any of the global or namespace rights is invalid.
        """
        self.__name = name
        self.__editable = editable

        _rights = []
        for right in rights:
            if right not in RIGHTS:
                raise ValueError(f'invalid value "{right}" in rights for group "{self.__name}"')
            _rights.append(right)
        self.__rights = tuple(_rights)

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
        return RIGHT_BOT in self.__rights

    @property
    def global_rights(self) -> typ.Sequence[str]:
        """This group’s global rights."""
        return self.__rights

    def has_right(self, right: str) -> bool:
        """
        Checks whether this group has the specified right.

        :param right: The right to check.
        :return: True if this group has the right, false otherwise.
        """
        return right in self.__rights

    def can_edit_pages_in_namespace(self, namespace) -> bool:
        """
        Checks whether this group can edit pages in the given namespace.

        :param namespace: Namespace to check.
        :type namespace: WikiPy.settings.Namespace
        :return: True if this group can edit pages in this namespace, false otherwise.
        """
        return RIGHT_EDIT_PAGES and all(self.has_right(r) for r in namespace.requires_rights)

    def __repr__(self):
        return f'{self.__name}[rights={self.__rights},editable={self.__editable}]'


__all__ = [
    'UserGroup',
]
