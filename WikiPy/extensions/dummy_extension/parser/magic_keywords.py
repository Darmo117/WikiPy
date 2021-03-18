import WikiPy.parser as parser


@parser.magic_keyword(takes_context=True)
def dummy(context):
    return context.page.full_title
