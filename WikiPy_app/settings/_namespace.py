import typing as typ


class Namespace:
    def __init__(self, ident: int, canonical_name: str, is_talk: bool, name: str = None, alias: str = None):
        self.__id = ident
        self.__canonical_name = canonical_name
        self.__name = name
        self.__alias = alias
        self.__is_talk = is_talk

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
    def alias(self) -> typ.Optional[str]:
        return self.__alias

    @property
    def is_talk(self):
        return self.__is_talk

    def get_name(self, local: bool, as_url: bool = False) -> str:
        if local and self.__name is not None:
            name = self.__name
        else:
            name = self.__canonical_name
        if as_url:
            from .. import api
            name = api.as_url_title(name)
        return name

    def matches_name(self, name: str) -> bool:
        name = name.lower()
        return (self.__canonical_name.lower() == name
                or self.__name is not None and self.__name.lower() == name
                or self.__alias is not None and self.__alias.lower() == name)
