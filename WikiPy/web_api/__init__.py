import json
import typing as typ
import xml.dom.minidom as xml_dom

import dicttoxml

from .. import settings, models
from ..api import emails as api_emails

__all__ = [
    'HELP_PAGE',
    'RESULT_PAGE',
    'RAW_RESULT',
    'handle_api',
]

HELP_PAGE = 'help'
RESULT_PAGE = 'result'
RAW_RESULT = 'raw_result'

HTML_CT = 'text/html'
JSON = 'json'
XML = 'xml'
content_types = {
    'json': ('application/json', JSON),
    'xml': ('application/xml', XML),
    'json_f': (HTML_CT, JSON),
    'xml_f': (HTML_CT, XML),
    'html': (HTML_CT, '')
}


def handle_api(user: models.User, params: typ.Dict[str, str]) -> typ.Tuple[typ.Dict[str, str], str]:
    lang_code = params.get('use_lang', settings.DEFAULT_LANGUAGE_CODE)
    language = settings.i18n.get_language(lang_code) or settings.i18n.get_language(settings.DEFAULT_LANGUAGE_CODE)
    actions = [name[8:] for name in globals() if name.startswith('_action_')]

    action = ''
    result_format = 'json_f'
    try:
        action = _get_param(params, 'action', actions, default='help')
        result_format = _get_param(params, 'format', content_types.keys(), default='json_f')
    except ValueError as e:
        message = str(e)
        if ':' in message:
            content = _build_invalid_value_error(*message.split(':'))
        else:
            content = _build_invalid_value_error(message, '')
        if locals().get('action') == 'help':
            action = ''
    else:
        content = globals()['_action_' + action](user, language, params)

    is_help = action == 'help'
    if is_help:
        result_format = 'html'
    is_raw = result_format in ['json', 'xml']
    pretty_print = not is_raw and not is_help

    content_type, data_type = content_types[result_format]

    if 'request_id' in params:
        # noinspection PyTypeChecker
        content['request_id'] = params['request_id']

    str_content = ''
    if data_type == JSON:
        str_content = json.dumps(content, indent=4 if pretty_print else None)
    elif data_type == XML:
        str_content = dicttoxml.dicttoxml(content, custom_root='api').decode(encoding='UTF-8')
        if pretty_print:
            tree = xml_dom.parseString(str_content)
            str_content = tree.toprettyxml(indent=' ' * 4)

    context = _get_context(content_type, str_content, language)
    if is_help:
        page_type = HELP_PAGE
    elif is_raw:
        page_type = RAW_RESULT
    else:
        page_type = RESULT_PAGE

    return context, page_type


def _get_param(params: typ.Mapping[str, str], name: str, values: typ.Iterable[str], default: str = None) -> str:
    value = params.get(name, default)
    if value is None:
        raise ValueError(name)
    if value == '':
        value = default
    if value not in values:
        raise ValueError(name + ':' + value)
    return value


def _build_invalid_value_error(param_name: str, param_value: str):
    return {
        'error': {
            'code': 'invalid_value',
            'message': f'Invalid value for parameter "{param_name}": "{param_value}"'
        }
    }


def _action_help(_1, _2, _3):
    return {}  # TODO générer la liste des modules


def _action_send_confirmation_email(user: models.User, _1, _2) -> typ.Dict[str, typ.Any]:
    sent = False
    if user.data.email_pending_confirmation:
        api_emails.send_email_change_confirmation_email(user, user.data.email_pending_confirmation)
        sent = True
    return {'sent': sent}


def _get_context(content_type: str, content: str, language: settings.i18n.Language) -> typ.Dict[str, str]:
    return {
        'project_name': settings.PROJECT_NAME,
        'content_type': content_type,
        'content': content,
        'language': language,
    }
