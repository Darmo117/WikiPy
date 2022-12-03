from django.apps import AppConfig


class WikiPyConfig(AppConfig):
    name = 'WikiPy'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Avoid circular imports
        from . import settings
        settings.post_load()
