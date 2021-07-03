"""
This module defines a command to minify static JS and CSS files of the WikiPy app.

This command should be absent from the release versions.
"""
import logging
import os
import pathlib
import re

import csscompressor
import rjsmin
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Minifies .js and .css files in static directory of WikiPy app.'

    def add_arguments(self, parser):
        parser.add_argument('directory', type=str, nargs='+', help='The directories to parse (not recursive)')

    def handle(self, *args, **options):
        for directory in options['directory']:
            logger.info(f'Searching in {directory}…')

            def f(fname: str) -> bool:
                return re.fullmatch(r'^.+(?<!\.min)\.(js|css)$', fname) is not None

            for filename in filter(f, os.listdir(directory)):
                path = os.path.join(directory, filename)
                if os.path.isfile(path):
                    logger.info(f'Minifying file {filename}…')

                    with open(path, encoding='UTF-8') as f_in:
                        contents = ''.join(f_in.readlines())
                        if filename.endswith('.js'):
                            minified_contents = rjsmin.jsmin(contents, keep_bang_comments=True)
                        elif filename.endswith('.css'):
                            minified_contents = csscompressor.compress(contents, preserve_exclamation_comments=True)
                        else:
                            logger.warning('Not .js or .css file, skipped.')
                            continue

                    basename = pathlib.Path(path).stem
                    ext = pathlib.Path(path).suffix
                    out_filename = f'{basename}.min{ext}'
                    with open(os.path.join(directory, out_filename), mode='w', encoding='UTF-8') as f_out:
                        f_out.write(minified_contents)

        logger.info('Done.')
