from . import errors


def api_action(*required_rights: str):
    """Decorator that declares the decorated function as an API action.

    :param required_rights: The rights the user must have to be able to perform the decorated action. May be empty.
    :return: The decorated function.
    :raises MissingRightError If the user is missing at least one of the required rights.
    """

    def aux(f):
        def wrapper(*args, **kwargs):
            performer = kwargs['performer']
            if performer:
                check_rights(performer, *required_rights)
            return f(*args, **kwargs)

        return wrapper

    return aux


def check_rights(performer, *rights: str):
    for right in rights:
        if not performer.has_right(right):
            raise errors.MissingRightError(right)
