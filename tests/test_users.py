import pytest
from django.contrib.auth import get_user_model
from apps.users.models import TenantMembership, TenantCredential

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="dev@example.com", password="pass1234")


@pytest.fixture
def membership(user):
    return TenantMembership.objects.create(
        user=user,
        provider="commcare",
        tenant_id="test-domain",
        tenant_name="Test Domain",
    )


class TestTenantCredential:
    def test_api_key_credential_fields(self, membership):
        cred = TenantCredential.objects.create(
            tenant_membership=membership,
            credential_type=TenantCredential.API_KEY,
            encrypted_credential="someencryptedvalue",
        )
        assert cred.pk is not None
        assert cred.credential_type == "api_key"

    def test_oauth_credential_fields(self, membership):
        cred = TenantCredential.objects.create(
            tenant_membership=membership,
            credential_type=TenantCredential.OAUTH,
        )
        assert cred.credential_type == "oauth"
        assert cred.encrypted_credential == ""

    def test_one_to_one_with_membership(self, membership):
        TenantCredential.objects.create(
            tenant_membership=membership,
            credential_type=TenantCredential.OAUTH,
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            TenantCredential.objects.create(
                tenant_membership=membership,
                credential_type=TenantCredential.OAUTH,
            )


class TestResolveCommcareDomains:
    def test_creates_tenant_credential_oauth(self, user, db):
        """resolve_commcare_domains must create TenantCredential(type=oauth) for each membership."""
        from unittest.mock import patch
        from apps.users.services.tenant_resolution import resolve_commcare_domains

        fake_domains = [
            {"domain_name": "domain-a", "project_name": "Domain A"},
            {"domain_name": "domain-b", "project_name": "Domain B"},
        ]
        with patch(
            "apps.users.services.tenant_resolution._fetch_all_domains",
            return_value=fake_domains,
        ):
            memberships = resolve_commcare_domains(user, "fake-token")

        assert len(memberships) == 2
        for tm in memberships:
            cred = TenantCredential.objects.get(tenant_membership=tm)
            assert cred.credential_type == TenantCredential.OAUTH
            assert cred.encrypted_credential == ""

    def test_idempotent_on_re_resolve(self, user, db):
        """Calling resolve twice does not create duplicate TenantCredentials."""
        from unittest.mock import patch
        from apps.users.services.tenant_resolution import resolve_commcare_domains

        fake_domains = [{"domain_name": "domain-a", "project_name": "Domain A"}]
        with patch(
            "apps.users.services.tenant_resolution._fetch_all_domains",
            return_value=fake_domains,
        ):
            resolve_commcare_domains(user, "fake-token")
            resolve_commcare_domains(user, "fake-token")

        assert TenantCredential.objects.filter(
            tenant_membership__user=user
        ).count() == 1
