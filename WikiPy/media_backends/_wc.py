"""
This module defines the Wikimedia Commons backend.
This backend cannot upload files.
"""
import requests


def load_backend():
    from . import MediaBackend, FileMetadata

    class WikimediaCommonsBackend(MediaBackend):
        """
        This media backend fetches files from Wikimedia Commons by using Mediawiki’s HTTP API.
        As such, it cannot upload files.
        """

        def __init__(self):
            super().__init__('wikimedia_commons', can_upload=False)

        def get_file_info(self, file_name):
            response = requests.get('https://commons.wikimedia.org/w/api.php', params={
                'action': 'query',
                'titles': 'File:' + file_name,
                'prop': 'imageinfo',
                'iiprop': 'url|mime|mediatype|size',
                'format': 'json',
            })
            json_obj = response.json()
            pages = json_obj['query']['pages']
            page = pages[list(pages.keys())[0]]

            if not page.get('imageinfo'):
                raise FileNotFoundError(file_name)

            metadata = page['imageinfo'][0]
            url = metadata['url']
            mime_type_full = metadata['mime']
            mime_type, mime_subtype = mime_type_full.split('/', maxsplit=1)
            width = metadata['width']

            media_type = {
                'BITMAP': FileMetadata.IMAGE,
                'VIDEO': FileMetadata.VIDEO,
                'AUDIO': FileMetadata.AUDIO,
            }.get(metadata['mediatype'])

            if media_type == FileMetadata.VIDEO:
                url_parts = url.split('/')
                url_parts.insert(5, 'thumb')
                thumb = f'{"/".join(url_parts)}/{width}px--{url.split("/")[-1]}.jpg'
            else:
                thumb = None

            return FileMetadata(
                url=url,
                media_type=media_type,
                mime_type_full=mime_type_full,
                mime_type=mime_type,
                mime_subtype=mime_subtype,
                video_thumbnail=thumb
            )

    return WikimediaCommonsBackend
