"""
Tests for OAuth token storage, encryption, retrieval, and refresh.
"""

from django.conf import settings


class TestTokenStorageSettings:
    """Verify allauth token storage is enabled."""

    def test_socialaccount_store_tokens_enabled(self):
        """allauth should be configured to persist OAuth tokens."""
        assert settings.SOCIALACCOUNT_STORE_TOKENS is True
