from django.apps import AppConfig


class BankingApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'banking_api'

    def ready(self):
        import banking_api.signals
