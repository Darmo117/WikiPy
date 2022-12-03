"""
This module defines the Namespace class.
"""
import typing as typ


class Namespace:
    def __init__(self, ident: int, canonical_name: str, has_talks: bool, can_be_main: bool, is_content: bool,
                 allows_subpages: bool, name: str = None, alias: str = None, feminine_name: str = None,
                 masculine_name: str = None, requires_rights: typ.Iterable[str] = None):
        """
        This class represents a namespace. Each namespace has an integer ID,
        a canonical name, an optional local name and an optional alias.

        :param ident: The namespace ID.
        :param canonical_name: The canonical name.
        :param has_talks: If true, pages in this namespace will have a talk page.
        :param can_be_main: If true, this namespace can be used as the main page’s namespace.
        :param is_content: If true, pages in this namespace will be considered to be a part of
            the actual content of the wiki.
        :param allows_subpages: If true, it will be possible to create subpages in this namespace.
        :param name: The optional local name. Used to translate default namespaces into the wiki’s language.
        :param alias: An optional alias.
        :param feminine_name: The feminine variant of the namespace name.
            Mainly intended for the User namespace in languages that have grammatical genders.
        :param masculine_name: The masculine variant of the namespace name.
            Mainly intended for the User namespace in languages that have grammatical genders.
        :param requires_rights: An optional list of rights users must have to be able to edit pages in this namespace.
        """
        self.__id = ident
        self.__canonical_name = canonical_name
        self.__name = name
        self.__alias = alias
        self.__feminine_name = feminine_name
        self.__masculine_name = masculine_name
        self.__has_talks = has_talks
        self.__can_be_main = can_be_main
        self.__is_content = is_content
        self.__allows_subpages = allows_subpages
        self.__requires_rights = tuple(requires_rights) if requires_rights else ()

    @property
    def id(self) -> int:
        """This namespace’s ID."""
        return self.__id

    @property
    def canonical_name(self) -> str:
        """This namespace’s canonical name."""
        return self.__canonical_name

    @property
    def name(self) -> typ.Optional[str]:
        """This namespace’s local name. May be None if undefined."""
        return self.__name

    @property
    def feminine_name(self) -> typ.Optional[str]:
        """This namespace’s feminine name variant. May be None if undefined."""
        return self.__feminine_name

    @property
    def masculine_name(self) -> typ.Optional[str]:
        """This namespace’s masculine name variant. May be None if undefined."""
        return self.__masculine_name

    @property
    def alias(self) -> typ.Optional[str]:
        """This namespace’s name alias. May be None if undefined."""
        return self.__alias

    @property
    def has_talks(self) -> bool:
        """Indicates whether pages in this namespace have talk pages."""
        return self.__has_talks

    @property
    def can_be_main(self) -> bool:
        """Indicates whether this namespace can be used as the main page’s namespace."""
        return self.__can_be_main

    @property
    def is_content(self) -> bool:
        """Indicates whether pages in this namespace have to be considered as the actual content of the wiki."""
        return self.__is_content

    @property
    def allows_subpages(self) -> bool:
        """Indicates whether pages in this namespace can have subpages."""
        return self.__allows_subpages

    @property
    def requires_rights(self) -> typ.Tuple[str]:
        """List of rights users must have to be able to edit pages in this namespace."""
        return self.__requires_rights

    def get_name(self, local: bool, gender=None, as_url: bool = False) -> str:
        """
        Returns the name of this namespace.

        :param local: If true, the local name is returned instead of the canonical one.
        :param gender: Gender to use.
        :type gender: WikiPy.models.Gender
        :param as_url: If true, returns a URL-compatible name.
        :return: The canonical or local name.
        """
        name = None

        if local:
            name = self.__name
            if gender:
                if gender.code == 'female' and self.__feminine_name:
                    name = self.__feminine_name
                elif gender.code == 'male' and self.__masculine_name:
                    name = self.__masculine_name
        if name is None:
            name = self.__canonical_name

        if as_url:
            from ..api import titles as api_titles
            name = api_titles.as_url_title(name)

        return name

    def matches_name(self, name: str) -> bool:
        """
        Tells whether the given name matches (case insensitive) any of the following properties on this namespace:
            - canonical name
            - local name
            - alias
            - feminine name
            - masculine name

        :param name: Name to test this namespace against.
        :return: True if the name matches any of the above properties, false otherwise.
        """
        name = name.lower()
        return (self.__canonical_name.lower() == name
                or self.__name is not None and self.__name.lower() == name
                or self.__alias is not None and self.__alias.lower() == name
                or self.__feminine_name is not None and self.__feminine_name.lower() == name
                or self.__masculine_name is not None and self.__masculine_name.lower() == name)
