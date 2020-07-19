class EmptyPageTitleException(ValueError):
    def __init__(self):
        super().__init__('empty page title')


class BadTitleException(ValueError):
    def __init__(self):
        super().__init__('invalid character in title')
