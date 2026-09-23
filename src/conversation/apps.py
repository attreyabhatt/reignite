from django.apps import AppConfig


class ConversationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'conversation'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from .web_conversion import on_web_login
        user_logged_in.connect(on_web_login, dispatch_uid="web_conversion_login")
