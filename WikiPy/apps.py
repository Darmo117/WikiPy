from django.apps import AppConfig


class WikiPyConfig(AppConfig):
    name = 'WikiPy'

    def ready(self):
        # Avoid circular imports
        from . import settings
        settings.post_load()
