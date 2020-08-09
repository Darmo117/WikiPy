from __future__ import annotations

import typing as typ

from ._config_values import *


class UserGroup:
    def __init__(self, name: str, label: str, hide_rc: bool, needs_validation: bool, global_rights: typ.Iterable[str],
                 namespace_edit_rights: typ.Dict[int, typ.Iterable[str]], editable: bool):
        self.__name = name
        self.__label = label
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
        return self.__name

    @property
    def label(self):
        return self.__label

    @property
    def editable(self):
        return self.__editable

    @property
    def hide_from_recent_changes(self) -> bool:
        return self.__hide_rc

    @property
    def needs_validation(self):
        return self.__needs_validation

    @property
    def global_rights(self) -> typ.Tuple[str]:
        return self.__global_rights

    @property
    def namespace_edit_rights(self) -> typ.Dict[int, typ.Tuple[str]]:
        return {k: v for k, v in self.__namespace_edit_rights.items()}

    def has_right(self, right: str) -> bool:
        return right in self.__global_rights

    def has_right_on_pages_in_namespace(self, right: str, namespace_id: int) -> bool:
        return self.has_right(right) and self.can_edit_pages_in_namespace(namespace_id)

    def can_read_pages_in_namespace(self, namespace_id: int):
        """
        Tells whether this group can read pages in the given namespace.
        :param namespace_id: Namespace ID to check.
        :return: True if this group read edit the page.
        """
        return RIGHT_READ_PAGES in self.__namespace_edit_rights[namespace_id]

    def can_edit_pages_in_namespace(self, namespace_id: int):
        """
        Tells whether this group can edit pages in the given namespace.
        :param namespace_id: Namespace ID to check.
        :return: True if this group can edit the page.
        """
        return RIGHT_EDIT_PAGES in self.__namespace_edit_rights[namespace_id]

    def __repr__(self):
        return f'{self.__name}[label={self.__label},hide_rc={self.__hide_rc},global_rights={self.__global_rights},' \
               f'namespace_rights={self.__namespace_edit_rights}]'
