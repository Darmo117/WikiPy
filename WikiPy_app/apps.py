from django.apps import AppConfig


class WikiPyAppConfig(AppConfig):
    name = 'WikiPy_app'

    def ready(self):
        # Avoid circular imports
        from . import settings
        settings.post_load()
