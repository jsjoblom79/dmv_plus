from django.apps import AppConfig


class ParentConfig(AppConfig):
    name = 'parent'

    def ready(self):
        import parent.services.parent_service
