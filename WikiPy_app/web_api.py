import typing as typ

from . import settings, api

HELP_PAGE = 'help'
RESULT_PAGE = 'result'
RAW_RESULT = 'raw_result'


def handle_api(user, params: typ.Dict[str, str]):
    if len(params) == 0:
        return _get_context('html', ''), HELP_PAGE
    else:
        try:
            action = params['action']
            if action == 'query':
                content_type = params.get('format', 'html')
                content = ''

                # TODO

                return (_get_context(content_type, content),
                        (RESULT_PAGE if content_type == 'html' else RAW_RESULT))
            elif action == 'submit':
                namespace_id = params['ns']
                title = params['title']
        except KeyError as e:
            return _get_context('html', str(e))


def _get_context(content_type: str, content: str):
    return {
        'project_name': settings.PROJECT_NAME,
        'content_type': content_type,
        'content': content,
        'language': 'en',
        'writing_direction': settings.WRITING_DIRECTION,
    }
