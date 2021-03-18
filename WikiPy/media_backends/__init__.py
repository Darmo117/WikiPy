import abc
import dataclasses
import typing as typ

import requests

__all__ = [
    'MediaBackend',
    'FileMetadata',
    'register_backend',
    'get_backends_ids',
    'get_backend',
    'register_default',
]


@dataclasses.dataclass(frozen=True)
class FileMetadata:
    IMAGE = 'BITMAP'
    VIDEO = 'VIDEO'
    AUDIO = 'AUDIO'

    url: str
    mime_type_full: str
    mime_type: str
    mime_subtype: str
    media_type: str
    video_thumbnail: str = None


class MediaBackend(abc.ABC):
    def __init__(self, name: str, can_upload: bool):
        self.__name = name
        self.__can_upload = can_upload

    @property
    def name(self) -> str:
        return self.__name

    @property
    def can_upload(self) -> bool:
        return self.__can_upload

    def upload_file(self, file):
        pass

    @abc.abstractmethod
    def get_file_info(self, file_name: str) -> typ.Optional[FileMetadata]:
        pass


class WikimediaCommonsBackend(MediaBackend):
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
            return None

        metadata = page['imageinfo'][0]
        url = metadata['url']
        mime_type_full = metadata['mime']
        mime_type, mime_subtype = mime_type_full.split('/', maxsplit=1)
        width = metadata['width']
        url_parts = url.split('/')
        url_parts.insert(5, 'thumb')

        return FileMetadata(
            url=url,
            media_type=metadata['mediatype'],
            mime_type_full=mime_type_full,
            mime_type=mime_type,
            mime_subtype=mime_subtype,
            video_thumbnail=f'{"/".join(url_parts)}/{width}px--{url.split("/")[-1]}.jpg'
        )


_BACKENDS: typ.Dict[str, MediaBackend] = {}


def register_backend(backend: MediaBackend):
    name = backend.name
    if name in _BACKENDS:
        raise ValueError(f'attempt to register 2 backends with the same name "{name}"')
    _BACKENDS[name] = backend


def get_backends_ids() -> typ.Sequence[str]:
    return list(_BACKENDS.keys())


def get_backend(name: str) -> typ.Optional[MediaBackend]:
    return _BACKENDS.get(name)


def register_default():
    register_backend(WikimediaCommonsBackend())
