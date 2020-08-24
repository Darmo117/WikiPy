class EmptyPageTitleException(ValueError):
    def __init__(self):
        super().__init__('empty page title')


class BadTitleException(ValueError):
    def __init__(self, character: str):
        super().__init__(character)


class PageException(ValueError):
    def __init__(self, message: str, page):
        super().__init__(message)
        self.__page = page

    @property
    def page(self):
        return self.__page


class PageEditForbidden(PageException):
    def __init__(self, page):
        super().__init__('user cannot edit page', page)


class PageReadForbidden(PageException):
    def __init__(self, page):
        super().__init__('user cannot read page', page)


class PageEditConflit(PageException):
    def __init__(self, page, revision, wikicode):
        super().__init__('page edit conflict', page)
        self.__revision = revision
        self.__wikicode = wikicode

    @property
    def revision(self):
        return self.__revision

    @property
    def wikicode(self):
        return self.__wikicode


class PageDoesNotExist(ValueError):
    def __init__(self, page_title: str):
        super().__init__(page_title)


class RevisionDoesNotExist(ValueError):
    def __init__(self, revision_id: int):
        super().__init__(str(revision_id))


class InvalidUsernameError(ValueError):
    pass


class DuplicateUsernameError(ValueError):
    pass


class InvalidPasswordError(ValueError):
    pass


class InvalidEmailError(ValueError):
    pass
