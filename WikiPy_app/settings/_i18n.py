_ENTRIES = {
    # Group names
    'group.all.name': 'All',
    'group.users.name': 'Users',
    'group.email_confirmed.name': 'Email Confirmed',
    'group.autoconfirmed.name': 'Autoconfirmed users',
    'group.patrollers.name': 'Patrollers',
    'group.administrators.name': 'Administrators',
    'group.bureaucrats.name': 'Bureaucrats',

    # Error pages
    'error.bad_title.title': 'Bad title',

    'link.talk.label': 'talk',
    'link.contributions.label': 'contributions',
}


def trans(key: str, **kwargs) -> str:
    return _ENTRIES.get(key, key) % kwargs
