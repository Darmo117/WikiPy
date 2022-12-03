"""
This module defines error classes used by the API.
"""


class EmptyPageTitleError(ValueError):
    """Error raised whenever the requested page title is empty."""

    def __init__(self):
        super().__init__('empty page title')


class BadTitleError(ValueError):
    """Error raised whenever the requested page title is invalid."""

    def __init__(self, character: str):
        super().__init__(character)


class ActionError(Exception):
    def __init__(self, code: str):
        super().__init__(code)


class PageError(Exception):
    """Base class for page-related errors."""

    def __init__(self, message: str, page):
        super().__init__(message)
        self.__page = page

    @property
    def page(self):
        return self.__page


class PageEditForbiddenError(PageError):
    """Error raised whenever a user tries to edit a page they are not allowed to edit."""

    def __init__(self, page):
        super().__init__('user cannot edit page', page)


class PageReadForbiddenError(PageError):
    """Error raised whenever a user tries to access a page they are not allowed to read."""

    def __init__(self, page):
        super().__init__('user cannot read page', page)


class PageProtectionForbiddenError(PageError):
    """Error raised whenever a user tries to set the protection level of a page but they do not have the permission."""

    def __init__(self, page):
        super().__init__('user cannot change page protection level', page)


class PageRenameForbiddenError(PageError):
    """Error raised whenever a user tries to rename a page they are not allowed to."""

    def __init__(self, page, code: str):
        super().__init__('user cannot rename this page', page)
        self.__code = code

    @property
    def code(self) -> str:
        return self.__code


class PageEditConflictError(PageError):
    """Error raised whenever there is an edit conflict."""

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


class RevisionDoesNotExistError(ValueError):
    """Error raised whenever a user requested a revision ID that does not exist."""

    def __init__(self, revision_id: int):
        super().__init__(str(revision_id))


class MissingRightError(Exception):
    """Error raised whenever a user does not have the permission required to perform an action."""

    def __init__(self, right: str):
        super().__init__(right)


class InvalidUsernameError(ValueError):
    """Indicates that the provided username is invalid."""


class DuplicateUsernameError(ValueError):
    """Indicates that the provided username already exists."""


class InvalidPasswordError(ValueError):
    """Indicates that the provided password is invalid."""


class InvalidEmailError(ValueError):
    """Indicates that the provided email address is invalid."""


class UserBlockDoesNotExistError(ValueError):
    """Raised whenever a user tries to delete a user block that does not exist."""
