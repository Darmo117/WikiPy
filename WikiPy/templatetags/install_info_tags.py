import typing as typ

import django.template as dj_template

from .. import page_context, parser, settings

register = dj_template.Library()


@register.inclusion_tag('WikiPy/tags/install-info-resource-table.html', takes_context=True)
def generate_resource_table(context: page_context.TemplateContext,
                            resources: typ.List[settings.resource_loader.ExternalResource], resource_type: str):
    return {
        'wpy_context': context.get('wpy_context'),
        'resource_type': resource_type,
        'resources': resources,
    }


@register.inclusion_tag('WikiPy/tags/install-info-parser-features-table.html', takes_context=True)
def generate_parser_feature_table(context: page_context.TemplateContext, features: typ.List[parser.ParserFeature],
                                  feature_type: str):
    return {
        'wpy_context': context.get('wpy_context'),
        'feature_type': feature_type,
        'features': features,
    }
