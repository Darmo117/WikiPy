import WikiPy_app.parser as parser


@parser.parser_function
def dummy(value):
    return value[::-1]
