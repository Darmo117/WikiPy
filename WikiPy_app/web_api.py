import typing as typ

from . import settings

HELP_PAGE = 'help'
RESULT_PAGE = 'result'
RAW_RESULT = 'raw_result'


def handle_api(params: typ.Dict[str, str]):
    if len(params) == 0:
        return _get_context('', '', 'en'), HELP_PAGE
    else:
        content_type = params.get('format', 'html')
        content = ''

        # TODO

        return _get_context(content_type, content, 'en'), (RESULT_PAGE if content_type == 'html' else RAW_RESULT)


def _get_context(content_type: str, content: str, lang: str):
    return {
        'project_name': settings.PROJECT_NAME,
        'content_type': content_type,
        'content': content,
        'lang': lang,
    }
