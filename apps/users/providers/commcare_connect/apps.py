"""Django app configuration for the CommCare Connect OAuth provider."""

from django.apps import AppConfig


class CommCareConnectProviderConfig(AppConfig):
    name = "apps.users.providers.commcare_connect"
    verbose_name = "CommCare Connect OAuth Provider"
