import typing as typ


class Namespace:
    def __init__(self, ident: int, name: str, is_talk: bool, local_name: str = None, alias: str = None):
        self.__id = ident
        self.__name = name
        self.__local_name = local_name
        self.__alias = alias
        self.__is_talk = is_talk

    @property
    def id(self) -> int:
        return self.__id

    @property
    def name(self) -> str:
        return self.__name

    @property
    def local_name(self) -> typ.Optional[str]:
        return self.__local_name

    @property
    def alias(self) -> typ.Optional[str]:
        return self.__alias

    @property
    def is_talk(self):
        return self.__is_talk

    def get_name(self, local: bool) -> str:
        if local and self.__local_name is not None:
            return self.__local_name
        else:
            return self.__name

    def matches_name(self, name: str) -> bool:
        name = name.lower()
        return (self.__name.lower() == name
                or self.__local_name is not None and self.__local_name.lower() == name
                or self.__alias is not None and self.__alias.lower() == name)
