import typing as typ


class Namespace:
    def __init__(self, ident: int, canonical_name: str, has_talks: bool, can_be_main: bool, is_content: bool,
                 allows_subpages: bool, name: str = None, alias: str = None, feminine_name: str = None,
                 masculine_name: str = None):
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

    @property
    def id(self) -> int:
        return self.__id

    @property
    def canonical_name(self) -> str:
        return self.__canonical_name

    @property
    def name(self) -> typ.Optional[str]:
        return self.__name

    @property
    def feminine_name(self) -> typ.Optional[str]:
        return self.__feminine_name

    @property
    def masculine_name(self) -> typ.Optional[str]:
        return self.__masculine_name

    @property
    def alias(self) -> typ.Optional[str]:
        return self.__alias

    @property
    def has_talks(self) -> bool:
        """Tells whether this namespace has talks."""
        return self.__has_talks

    @property
    def can_be_main(self) -> bool:
        """Tells whether this namespace can be used as the main page’s namespace."""
        return self.__can_be_main

    @property
    def is_content(self) -> bool:
        return self.__is_content

    @property
    def allows_subpages(self) -> bool:
        return self.__allows_subpages

    def get_name(self, local: bool, gender=None, as_url: bool = False) -> str:
        """
        Returns the name of this namespace.

        :param local: If true, local name is returned instead of canonical.
        :param gender: Gender of the user page. Only used if namespace is User: or User Talk:.
        :type gender: WikiPy.models.Gender
        :param as_url: If true, returns a URL-compatible name.
        :return: The name.
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
        Tells whether the given name matches any of the following properties (case insensitive):
        canonical name, local name, alias, feminine name, masculine name.

        :param name: Name to test this namespace against.
        :return: True if and only if the name matches any of the above properties; False otherwise.
        """
        name = name.lower()
        return (self.__canonical_name.lower() == name
                or self.__name is not None and self.__name.lower() == name
                or self.__alias is not None and self.__alias.lower() == name
                or self.__feminine_name is not None and self.__feminine_name.lower() == name
                or self.__masculine_name is not None and self.__masculine_name.lower() == name)
