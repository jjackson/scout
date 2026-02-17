"""URL configuration for CommCare Connect OAuth provider."""

from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import CommCareConnectProvider

urlpatterns = default_urlpatterns(CommCareConnectProvider)
