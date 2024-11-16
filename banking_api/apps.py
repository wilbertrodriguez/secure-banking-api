from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class BankingApiConfig(AppConfig):
    # This is the default auto field for database IDs
    default_auto_field = 'django.db.models.BigAutoField'
    
    # Name of your Django app
    name = 'banking_api'

    def ready(self):
        # Import the signals module to ensure they are registered when the app is ready
        import banking_api.signals
        logger.info("Banking API signals loaded successfully.")
