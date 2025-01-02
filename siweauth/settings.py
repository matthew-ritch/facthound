from django.conf import settings

# SIWE message validity window in minutes
SIWE_MESSAGE_VALIDITY = getattr(settings, 'SIWE_MESSAGE_VALIDITY', 5)

# Expected chain ID for SIWE messages
SIWE_CHAIN_ID = getattr(settings, 'SIWE_CHAIN_ID', 1)

# Expected domain for SIWE messages
SIWE_DOMAIN = getattr(settings, 'SIWE_DOMAIN', 'testhost')

# Expected URI for SIWE messages
SIWE_URI = getattr(settings, 'SIWE_URI', 'https://testhost/api/token/')
