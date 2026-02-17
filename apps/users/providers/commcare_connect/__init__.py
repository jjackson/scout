"""
CommCare Connect OAuth2 provider for django-allauth.

CommCare Connect is a separate service from CommCare HQ with its own
OAuth application and endpoints.

Usage:
    1. Add 'apps.users.providers.commcare_connect' to INSTALLED_APPS
    2. Configure OAuth app credentials via Django admin (SocialApp model)
    3. The provider will be available at /accounts/commcare_connect/login/
"""

default_app_config = "apps.users.providers.commcare_connect.apps.CommCareConnectProviderConfig"
