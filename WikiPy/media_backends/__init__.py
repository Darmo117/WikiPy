"""
This module defines classes and functions to related to media backends.

Media backends are used to access multimedia files from wiki pages.
"""
import abc
import dataclasses
import importlib
import logging
import os
import typing as typ

from .. import settings


class UploadNotSupportedError(RuntimeError):
    """
    Raised when there was an attempt to call the upload_file method
    on a MediaBackend instance that does not support file upload.
    """


@dataclasses.dataclass(frozen=True)
class FileMetadata:
    """
    Every file has metadata describing its type, where it is stored, etc.

    There are only 3 file types:
        - BITMAP for images
        - VIDEO for videos
        - AUDIO for audio-only files
    """
    IMAGE = 'IMAGE'
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
        """
        A media backend is a proxy that can retrieve files metadata and may be used to upload files.

        :param name: Backend’s unique name.
        :param can_upload: If true, this backend may be used to upload files.
        """
        self.__name = name
        self.__can_upload = can_upload

    @property
    def name(self) -> str:
        """This backend’s name."""
        return self.__name

    @property
    def can_upload(self) -> bool:
        """Whether this backend can upload files."""
        return self.__can_upload

    def upload_file(self, file):
        """
        Uploads the given file.

        :param file: The file to upload.
        :raises UploadNotSupportedError: If this media backend cannot upload files.
        """
        if not self.can_upload:
            raise UploadNotSupportedError('file upload is not supported by this media backend')
        self._upload_file(file)

    def _upload_file(self, file):
        """
        Uploads the given file.

        :param file: The file to upload.
        """
        pass

    @abc.abstractmethod
    def get_file_info(self, file_name: str) -> typ.Optional[FileMetadata]:
        """
        Returns metadata for the given file.

        :param file_name: Name of the file for which metadata has to be fetched.
        :return: The file’s metadata.
        :raises FileNotFoundError: If the file does not exist.
        """
        pass


_BACKENDS: typ.Dict[str, MediaBackend] = {}


def register_backend(backend: MediaBackend):
    """
    Registers a media backend.

    :param backend: The backend instance to register.
    :raises ValueError: If another backend with the same name is already registered.
    """
    name = backend.name
    logging.info(f'Registering media backend "{name}"…')
    if name in _BACKENDS:
        raise ValueError(f'attempt to register 2 backends with the same name "{name}"')
    _BACKENDS[name] = backend
    logging.info(f'Media backend "{name}" registered successfully.')


def get_backends_ids() -> typ.Sequence[str]:
    """Returns the list of all registered media backend IDs."""
    return list(_BACKENDS.keys())


def get_backend(name: str) -> typ.Optional[MediaBackend]:
    """
    Returns the media backend with the given name.

    :param name: The backend’s name.
    :return: The backend or None if the name is undefined.
    """
    return _BACKENDS.get(name)


def register_default():
    """Registers the default media backends."""
    logging.info('Loading default media backends…')
    files = filter(
        lambda d: os.path.isfile(os.path.join(settings.WIKI_APP_DIR, 'media_backends', d)) and d.endswith('.py') and not d.startswith('__'),
        os.listdir(os.path.join(settings.WIKI_APP_DIR, 'media_backends'))
    )
    for file in files:
        module_name = file[:-3]
        try:
            module = importlib.import_module('.' + module_name, package=__name__)
        except ModuleNotFoundError:  # Should never happen
            logging.error(f'Module "{__name__}.{module_name}" not found, skipping backend.')
            continue
        try:
            # noinspection PyUnresolvedReferences
            cls = module.load_backend()
        except (AttributeError, TypeError):
            logging.error(f'Function "load_backend" not found, skipping backend.')
            continue
        register_backend(cls())

    logging.info('Default media backends loaded.')


__all__ = [
    'MediaBackend',
    'FileMetadata',
    'register_backend',
    'get_backends_ids',
    'get_backend',
    'register_default',
]
