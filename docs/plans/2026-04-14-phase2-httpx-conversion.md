# Phase 2: Replace `requests` with `httpx` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate all 7 `sync_to_async` wrappers in `apps/users/` by converting sync `requests` calls to native `httpx.AsyncClient` calls.

**Architecture:** Four service files (`tenant_verification.py`, `tenant_resolution.py`, `token_refresh.py`, `credential_resolver.py`) get async replacements using `httpx.AsyncClient`. The sync originals are removed (no dual sync/async). Views call the async functions directly, dropping `sync_to_async`. One `sync_to_async(_create)` call is replaced with direct async ORM calls (idempotent upserts, no atomic block needed).

**Tech Stack:** `httpx` (HTTP client), `pytest-httpx` (test mocking), Django async ORM

**Scope note:** The allauth provider views (`commcare/views.py`, `commcare_connect/views.py`) also use `requests` but are called by allauth's sync OAuth flow — out of scope.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `pyproject.toml` | Add `httpx` + `pytest-httpx` deps |
| Modify | `apps/users/services/tenant_verification.py` | `verify_commcare_credential` → async with httpx |
| Modify | `tests/test_tenant_verification.py` | Switch from `unittest.mock` to `pytest-httpx` |
| Modify | `apps/users/services/tenant_resolution.py` | All 3 functions → async with httpx + async ORM |
| Modify | `tests/test_tenant_resolution.py` | Async tests with `pytest-httpx` |
| Modify | `tests/test_connect_tenant_resolution.py` | Async tests with `pytest-httpx` |
| Modify | `apps/users/services/token_refresh.py` | `refresh_oauth_token` → async with httpx |
| Modify | `tests/test_oauth_tokens.py` | `TestTokenRefresh` class → `pytest-httpx` |
| Modify | `apps/users/services/credential_resolver.py` | `_resolve_oauth_credential` → async, remove `sync_to_async` |
| Modify | `apps/users/views.py` | Remove all `sync_to_async` wrappers, call async functions directly |
| Modify | `tests/test_tenant_api.py` | Update if it patches `requests` on the old import path |
| Modify | `tests/test_tenant_ensure_api.py` | Update if it patches `requests` on the old import path |

---

### Task 1: Add `httpx` and `pytest-httpx` dependencies

**Files:**
- Modify: `pyproject.toml:8` (dependencies) and `pyproject.toml:92` (dependency-groups.dev)

- [ ] **Step 1: Add httpx to project dependencies and pytest-httpx to dev**

In `pyproject.toml`, add `"httpx>=0.27"` to the `[project.dependencies]` list (after the Django section) and `"pytest-httpx>=0.35"` to `[dependency-groups] dev`.

```toml
# In [project] dependencies, after "django-environ>=0.11",
"httpx>=0.27",

# In [dependency-groups] dev, after "requests-mock>=1.12.1",
"pytest-httpx>=0.35",
```

- [ ] **Step 2: Install dependencies**

Run: `uv sync`
Expected: Clean install with httpx and pytest-httpx resolved.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "deps: add httpx and pytest-httpx for async HTTP migration"
```

---

### Task 2: Convert `tenant_verification.py` to async httpx (2a)

**Files:**
- Modify: `apps/users/services/tenant_verification.py`
- Modify: `tests/test_tenant_verification.py`

- [ ] **Step 1: Rewrite tests to async with pytest-httpx**

Replace `tests/test_tenant_verification.py` contents:

```python
import httpx
import pytest


class TestVerifyCommcareCredential:
    @pytest.mark.asyncio
    async def test_valid_credential_returns_domain_info(self, httpx_mock):
        from apps.users.services.tenant_verification import verify_commcare_credential

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            json={
                "objects": [
                    {"domain_name": "dimagi", "project_name": "Dimagi"},
                    {"domain_name": "other", "project_name": "Other"},
                ]
            },
        )

        result = await verify_commcare_credential(
            domain="dimagi", username="user@dimagi.org", api_key="secret"
        )

        assert result["domain_name"] == "dimagi"
        request = httpx_mock.get_request()
        assert "/api/user_domains/v1/" in str(request.url)
        assert request.headers["Authorization"] == "ApiKey user@dimagi.org:secret"

    @pytest.mark.asyncio
    async def test_invalid_credential_raises(self, httpx_mock):
        from apps.users.services.tenant_verification import (
            CommCareVerificationError,
            verify_commcare_credential,
        )

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            status_code=401,
        )

        with pytest.raises(CommCareVerificationError):
            await verify_commcare_credential(
                domain="dimagi", username="user@dimagi.org", api_key="wrong"
            )

    @pytest.mark.asyncio
    async def test_forbidden_raises(self, httpx_mock):
        from apps.users.services.tenant_verification import (
            CommCareVerificationError,
            verify_commcare_credential,
        )

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            status_code=403,
        )

        with pytest.raises(CommCareVerificationError):
            await verify_commcare_credential(
                domain="dimagi", username="user@dimagi.org", api_key="wrong"
            )

    @pytest.mark.asyncio
    async def test_server_error_raises(self, httpx_mock):
        from apps.users.services.tenant_verification import (
            CommCareVerificationError,
            verify_commcare_credential,
        )

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            status_code=500,
            text="Internal Server Error",
        )

        with pytest.raises(CommCareVerificationError, match="unexpected status 500"):
            await verify_commcare_credential(
                domain="dimagi", username="user@dimagi.org", api_key="secret"
            )

    @pytest.mark.asyncio
    async def test_wrong_domain_raises(self, httpx_mock):
        from apps.users.services.tenant_verification import (
            CommCareVerificationError,
            verify_commcare_credential,
        )

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            json={"objects": [{"domain_name": "some-other-domain", "project_name": "Other"}]},
        )

        with pytest.raises(CommCareVerificationError, match="not a member of domain"):
            await verify_commcare_credential(
                domain="dimagi", username="user@dimagi.org", api_key="secret"
            )

    @pytest.mark.asyncio
    async def test_no_domains_raises(self, httpx_mock):
        from apps.users.services.tenant_verification import (
            CommCareVerificationError,
            verify_commcare_credential,
        )

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            json={"objects": []},
        )

        with pytest.raises(CommCareVerificationError, match="not a member of domain"):
            await verify_commcare_credential(
                domain="dimagi", username="user@dimagi.org", api_key="secret"
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_tenant_verification.py -v`
Expected: FAIL — `verify_commcare_credential` is still sync.

- [ ] **Step 3: Convert the service to async httpx**

Replace `apps/users/services/tenant_verification.py` contents:

```python
"""Verify provider credentials before creating Tenant records."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

COMMCARE_API_BASE = "https://www.commcarehq.org"


class CommCareVerificationError(Exception):
    """Raised when CommCare credential verification fails."""


async def verify_commcare_credential(domain: str, username: str, api_key: str) -> dict:
    """Verify a CommCare API key using the user domain list API.

    Calls GET /api/user_domains/v1/ with the supplied API key and checks that
    the specified domain appears in the returned list of domains.

    Returns a dict with domain info on success.

    Raises CommCareVerificationError if the credential is invalid or the user
    is not a member of the domain.
    """
    url = f"{COMMCARE_API_BASE}/api/user_domains/v1/"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"ApiKey {username}:{api_key}"},
        )
    if resp.status_code in (401, 403):
        raise CommCareVerificationError(
            f"CommCare rejected the API key (HTTP {resp.status_code})"
        )
    if not resp.is_success:
        logger.warning(
            "CommCare verification failed: username=%s status=%s body=%s",
            username,
            resp.status_code,
            resp.text[:500],
        )
        raise CommCareVerificationError(
            f"CommCare API returned unexpected status {resp.status_code}"
        )
    data = resp.json()
    for entry in data.get("objects", []):
        if entry.get("domain_name") == domain:
            return entry
    raise CommCareVerificationError(f"User '{username}' is not a member of domain '{domain}'")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_tenant_verification.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/users/services/tenant_verification.py tests/test_tenant_verification.py
git commit -m "feat(users): convert verify_commcare_credential to async httpx"
```

---

### Task 3: Convert `tenant_resolution.py` to async httpx + async ORM (2b)

**Files:**
- Modify: `apps/users/services/tenant_resolution.py`
- Modify: `tests/test_tenant_resolution.py`
- Modify: `tests/test_connect_tenant_resolution.py`

- [ ] **Step 1: Rewrite `test_tenant_resolution.py` as async with pytest-httpx**

```python
import pytest


@pytest.mark.django_db
class TestResolveCommcareDomains:
    @pytest.mark.asyncio
    async def test_fetches_and_stores_domains(self, user, httpx_mock):
        from apps.users.services.tenant_resolution import resolve_commcare_domains

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            json={
                "meta": {"limit": 20, "offset": 0, "total_count": 2, "next": None},
                "objects": [
                    {"domain_name": "dimagi", "project_name": "Dimagi"},
                    {"domain_name": "test-project", "project_name": "Test Project"},
                ],
            },
        )

        memberships = await resolve_commcare_domains(user, "fake-token")

        assert len(memberships) == 2
        assert memberships[0].tenant.external_id == "dimagi"
        assert memberships[1].tenant.external_id == "test-project"

        from apps.users.models import TenantMembership

        assert await TenantMembership.objects.filter(user=user).acount() == 2

    @pytest.mark.asyncio
    async def test_updates_existing_memberships(self, user, httpx_mock):
        from apps.users.models import Tenant, TenantMembership

        tenant = await Tenant.objects.acreate(
            provider="commcare", external_id="dimagi", canonical_name="Old Name"
        )
        await TenantMembership.objects.acreate(user=user, tenant=tenant)

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            json={
                "meta": {"limit": 20, "offset": 0, "total_count": 1, "next": None},
                "objects": [{"domain_name": "dimagi", "project_name": "New Name"}],
            },
        )

        await resolve_commcare_domains(user, "fake-token")

        await tenant.arefresh_from_db()
        assert tenant.canonical_name == "New Name"

    @pytest.mark.asyncio
    async def test_auth_error_raises(self, user, httpx_mock):
        from apps.users.services.tenant_resolution import CommCareAuthError

        httpx_mock.add_response(
            url="https://www.commcarehq.org/api/user_domains/v1/",
            status_code=401,
        )

        with pytest.raises(CommCareAuthError):
            await resolve_commcare_domains(user, "fake-token")
```

- [ ] **Step 2: Rewrite `test_connect_tenant_resolution.py` as async with pytest-httpx**

```python
import pytest

from apps.users.services.tenant_resolution import ConnectAuthError, resolve_connect_opportunities


@pytest.mark.django_db
class TestResolveConnectOpportunities:
    @pytest.mark.asyncio
    async def test_fetches_and_stores_opportunities(self, user, httpx_mock):
        httpx_mock.add_response(
            json={
                "opportunities": [
                    {"id": 42, "name": "Opp 42"},
                    {"id": 99, "name": "Test Opp"},
                ],
            },
        )

        memberships = await resolve_connect_opportunities(user, "fake-token")

        assert len(memberships) == 2
        assert memberships[0].tenant.provider == "commcare_connect"
        assert memberships[0].tenant.external_id == "42"
        assert memberships[0].tenant.canonical_name == "Opp 42"
        assert memberships[1].tenant.external_id == "99"
        assert memberships[1].tenant.canonical_name == "Test Opp"

        from apps.users.models import TenantCredential, TenantMembership

        assert (
            await TenantMembership.objects.filter(
                user=user, tenant__provider="commcare_connect"
            ).acount()
            == 2
        )

        async for tm in TenantMembership.objects.filter(
            user=user, tenant__provider="commcare_connect"
        ):
            assert await TenantCredential.objects.filter(
                tenant_membership=tm, credential_type=TenantCredential.OAUTH
            ).aexists()

    @pytest.mark.asyncio
    async def test_updates_existing_opportunity_name(self, user, httpx_mock):
        from apps.users.models import Tenant, TenantMembership

        tenant = await Tenant.objects.acreate(
            provider="commcare_connect", external_id="42", canonical_name="Old Name"
        )
        await TenantMembership.objects.acreate(user=user, tenant=tenant)

        httpx_mock.add_response(
            json={
                "opportunities": [
                    {"id": 42, "name": "New Name"},
                ],
            },
        )

        await resolve_connect_opportunities(user, "fake-token")

        await tenant.arefresh_from_db()
        assert tenant.canonical_name == "New Name"

    @pytest.mark.asyncio
    async def test_auth_error_raises(self, user, httpx_mock):
        httpx_mock.add_response(status_code=401)

        with pytest.raises(ConnectAuthError):
            await resolve_connect_opportunities(user, "fake-token")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_tenant_resolution.py tests/test_connect_tenant_resolution.py -v`
Expected: FAIL — functions are still sync.

- [ ] **Step 4: Convert the service to async**

Replace `apps/users/services/tenant_resolution.py` contents:

```python
"""
Tenant resolution for OAuth providers.

After a user authenticates, this service queries the provider's API
to discover which tenants (domains/organizations) the user belongs to,
and stores them as TenantMembership records.
"""

from __future__ import annotations

import logging

import httpx

from apps.users.models import Tenant, TenantCredential, TenantMembership

logger = logging.getLogger(__name__)

COMMCARE_DOMAIN_API = "https://www.commcarehq.org/api/user_domains/v1/"


class CommCareAuthError(Exception):
    """Raised when CommCare returns a 401/403 during domain resolution."""


class ConnectAuthError(Exception):
    """Raised when Connect returns a 401/403 during opportunity resolution."""


async def resolve_commcare_domains(user, access_token: str) -> list[TenantMembership]:
    """Fetch the user's CommCare domains and upsert TenantMembership records."""
    domains = await _fetch_all_domains(access_token)
    memberships = []

    for domain in domains:
        tenant, _ = await Tenant.objects.aupdate_or_create(
            provider="commcare",
            external_id=domain["domain_name"],
            defaults={"canonical_name": domain["project_name"]},
        )
        tm, _ = await TenantMembership.objects.aget_or_create(user=user, tenant=tenant)
        await TenantCredential.objects.aget_or_create(
            tenant_membership=tm,
            defaults={"credential_type": TenantCredential.OAUTH},
        )
        memberships.append(tm)

    logger.info(
        "Resolved %d CommCare domains for user %s",
        len(memberships),
        user.email,
    )
    return memberships


async def resolve_connect_opportunities(user, access_token: str) -> list[TenantMembership]:
    """Fetch the user's Connect opportunities and upsert TenantMembership records."""
    try:
        from django.conf import settings

        base_url = getattr(settings, "CONNECT_API_URL", "https://connect.dimagi.com")
    except ImportError:
        base_url = "https://connect.dimagi.com"

    url = f"{base_url.rstrip('/')}/export/opp_org_program_list/"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code in (401, 403):
        raise ConnectAuthError(
            f"Connect returned {resp.status_code} — access token may have expired"
        )
    resp.raise_for_status()

    opportunities = resp.json().get("opportunities", [])
    memberships = []

    for opp in opportunities:
        tenant, _ = await Tenant.objects.aupdate_or_create(
            provider="commcare_connect",
            external_id=str(opp["id"]),
            defaults={"canonical_name": opp["name"]},
        )
        tm, _ = await TenantMembership.objects.aget_or_create(user=user, tenant=tenant)
        await TenantCredential.objects.aget_or_create(
            tenant_membership=tm,
            defaults={"credential_type": TenantCredential.OAUTH},
        )
        memberships.append(tm)

    logger.info(
        "Resolved %d Connect opportunities for user %s",
        len(memberships),
        user.email,
    )
    return memberships


async def _fetch_all_domains(access_token: str) -> list[dict]:
    """Paginate through the CommCare user_domains API.

    Raises CommCareAuthError on 401/403 so callers can distinguish an
    expired token from a generic server error.
    """
    results = []
    url = COMMCARE_DOMAIN_API
    async with httpx.AsyncClient(timeout=30) as client:
        while url:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code in (401, 403):
                raise CommCareAuthError(
                    f"CommCare returned {resp.status_code} — access token may have expired"
                )
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("objects", []))
            next_url = data.get("meta", {}).get("next")
            if next_url and next_url.startswith(COMMCARE_DOMAIN_API.split("/api/")[0]):
                url = next_url
            else:
                url = None
    return results
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_tenant_resolution.py tests/test_connect_tenant_resolution.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/users/services/tenant_resolution.py tests/test_tenant_resolution.py tests/test_connect_tenant_resolution.py
git commit -m "feat(users): convert tenant resolution to async httpx + async ORM"
```

---

### Task 4: Convert `token_refresh.py` to async httpx (2c)

**Files:**
- Modify: `apps/users/services/token_refresh.py`
- Modify: `tests/test_oauth_tokens.py` (only `TestTokenRefresh` class)

- [ ] **Step 1: Rewrite `TestTokenRefresh` in `tests/test_oauth_tokens.py` to async with pytest-httpx**

Replace only the `TestTokenRefresh` class (leave all other classes unchanged):

```python
class TestTokenRefresh:
    """Test the OAuth token refresh service."""

    @pytest.mark.asyncio
    async def test_refresh_updates_token(self, httpx_mock):
        from apps.users.services.token_refresh import refresh_oauth_token

        token_url = "https://www.commcarehq.org/oauth/token/"
        httpx_mock.add_response(
            url=token_url,
            method="POST",
            json={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 3600,
            },
        )

        social_token = MagicMock()
        social_token.token = "old_access_token"
        social_token.token_secret = "old_refresh_token"
        social_token.app.client_id = "client_123"
        social_token.app.secret = "secret_456"
        social_token.asave = AsyncMock()

        result = await refresh_oauth_token(social_token, token_url)

        assert result == "new_access_token"
        assert social_token.token == "new_access_token"
        assert social_token.token_secret == "new_refresh_token"
        social_token.asave.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refresh_failure_raises(self, httpx_mock):
        from apps.users.services.token_refresh import (
            TokenRefreshError,
            refresh_oauth_token,
        )

        token_url = "https://example.com/oauth/token/"
        httpx_mock.add_response(url=token_url, method="POST", status_code=400)

        social_token = MagicMock()
        social_token.token_secret = "old_refresh_token"
        social_token.app.client_id = "client_123"
        social_token.app.secret = "secret_456"

        with pytest.raises(TokenRefreshError):
            await refresh_oauth_token(social_token, token_url)
```

Also add `from unittest.mock import AsyncMock` to the existing imports at the top of the file (alongside the existing `MagicMock` and `patch` imports).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_oauth_tokens.py::TestTokenRefresh -v`
Expected: FAIL — `refresh_oauth_token` is still sync.

- [ ] **Step 3: Convert the service to async**

Replace `apps/users/services/token_refresh.py` contents:

```python
"""OAuth token refresh service.

Handles refreshing expired OAuth tokens for CommCare providers.
Called proactively (before token expires) and reactively (after 401).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx
from django.utils import timezone

logger = logging.getLogger(__name__)

# Refresh tokens that expire within this window
REFRESH_BUFFER = timedelta(minutes=5)

PROVIDER_TOKEN_URLS = {
    "commcare": "https://www.commcarehq.org/oauth/token/",
    "commcare_connect": "https://connect.dimagi.com/o/token/",
}


class TokenRefreshError(Exception):
    """Raised when token refresh fails."""


def token_needs_refresh(expires_at: timezone.datetime | None) -> bool:
    """Check if a token needs refreshing based on its expiry time.

    Returns True if the token expires within REFRESH_BUFFER.
    Returns False if expires_at is None (unknown expiry -- assume valid).
    """
    if expires_at is None:
        return False
    return timezone.now() + REFRESH_BUFFER >= expires_at


async def refresh_oauth_token(social_token, token_url: str) -> str:
    """Refresh an OAuth token using the refresh token grant.

    Args:
        social_token: allauth SocialToken instance with token_secret (refresh token)
            and app (SocialApp with client_id and secret).
        token_url: The provider's token endpoint URL.

    Returns:
        The new access token string.

    Raises:
        TokenRefreshError: If the refresh request fails.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": social_token.token_secret,
                    "client_id": social_token.app.client_id,
                    "client_secret": social_token.app.secret,
                },
            )
            response.raise_for_status()
    except Exception as e:
        logger.error("Token refresh failed for app %s: %s", social_token.app.client_id, e)
        raise TokenRefreshError(f"Failed to refresh OAuth token: {e}") from e

    data = response.json()
    social_token.token = data["access_token"]
    if data.get("refresh_token"):
        social_token.token_secret = data["refresh_token"]
    if data.get("expires_in"):
        social_token.expires_at = timezone.now() + timedelta(seconds=data["expires_in"])
    await social_token.asave()

    logger.info("Successfully refreshed OAuth token for app %s", social_token.app.client_id)
    return social_token.token
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_oauth_tokens.py::TestTokenRefresh -v`
Expected: Both tests PASS.

- [ ] **Step 5: Run all token-related tests**

Run: `uv run pytest tests/test_oauth_tokens.py tests/test_token_refresh_urls.py -v`
Expected: All PASS. The `token_needs_refresh` tests are sync and unchanged. `TestTokenRefreshUrls` imports `PROVIDER_TOKEN_URLS` from `apps/users/auth_views` (not the service file), so it's unaffected.

- [ ] **Step 6: Commit**

```bash
git add apps/users/services/token_refresh.py tests/test_oauth_tokens.py
git commit -m "feat(users): convert refresh_oauth_token to async httpx"
```

---

### Task 5: Convert `credential_resolver.py` — make `_resolve_oauth_credential` async (2c/2d)

**Files:**
- Modify: `apps/users/services/credential_resolver.py:106-123`

- [ ] **Step 1: Convert `_resolve_oauth_credential` to async and remove `sync_to_async`**

In `credential_resolver.py`, make two changes:

1. Remove the `sync_to_async` import (line 8).
2. Replace the `sync_to_async` call on line 106 and make `_resolve_oauth_credential` async:

Replace in `credential_resolver.py`:

Line 8 — change:
```python
from asgiref.sync import sync_to_async
```
to: remove this line entirely.

Lines 106-123 — replace:
```python
    return await sync_to_async(_resolve_oauth_credential)(token_obj, provider)


def _resolve_oauth_credential(token_obj, provider: str) -> dict:
    """Build an OAuth credential dict, refreshing the token if near expiry."""
    token_value = token_obj.token

    if token_needs_refresh(token_obj.expires_at):
        token_url = PROVIDER_TOKEN_URLS.get(provider)
        if token_url and token_obj.token_secret:
            try:
                token_value = refresh_oauth_token(token_obj, token_url)
            except TokenRefreshError:
                logger.warning(
                    "Token refresh failed for provider %s, using existing token", provider
                )

    return {"type": "oauth", "value": token_value}
```

with:

```python
    return await _aresolve_oauth_credential(token_obj, provider)


async def _aresolve_oauth_credential(token_obj, provider: str) -> dict:
    """Build an OAuth credential dict, refreshing the token if near expiry."""
    token_value = token_obj.token

    if token_needs_refresh(token_obj.expires_at):
        token_url = PROVIDER_TOKEN_URLS.get(provider)
        if token_url and token_obj.token_secret:
            try:
                token_value = await refresh_oauth_token(token_obj, token_url)
            except TokenRefreshError:
                logger.warning(
                    "Token refresh failed for provider %s, using existing token", provider
                )

    return {"type": "oauth", "value": token_value}
```

- [ ] **Step 2: Run existing credential resolver tests**

Run: `uv run pytest tests/ -k "credential" -v`
Expected: PASS (if tests exist) or no tests found (the existing tests for credential_resolver are integration tests within tenant_api tests).

- [ ] **Step 3: Commit**

```bash
git add apps/users/services/credential_resolver.py
git commit -m "feat(users): convert _resolve_oauth_credential to async, remove sync_to_async"
```

---

### Task 6: Update views.py — remove all `sync_to_async` wrappers (2a/2b/2e)

**Files:**
- Modify: `apps/users/views.py`

- [ ] **Step 1: Remove `sync_to_async` import and update all call sites**

In `apps/users/views.py`:

1. **Line 8** — remove the `sync_to_async` import:
   ```python
   # DELETE this line:
   from asgiref.sync import sync_to_async
   ```

2. **Line 52** — `resolve_commcare_domains` (already async now, call directly):
   ```python
   # Change:
   await sync_to_async(resolve_commcare_domains)(user, access_token)
   # To:
   await resolve_commcare_domains(user, access_token)
   ```

3. **Line 65** — `resolve_connect_opportunities` (already async):
   ```python
   # Change:
   await sync_to_async(resolve_connect_opportunities)(user, connect_token)
   # To:
   await resolve_connect_opportunities(user, connect_token)
   ```

4. **Line 172** — `verify_commcare_credential` (already async):
   ```python
   # Change:
   await sync_to_async(verify_commcare_credential)(
       domain=tenant_id, username=cc_username, api_key=cc_api_key
   )
   # To:
   await verify_commcare_credential(
       domain=tenant_id, username=cc_username, api_key=cc_api_key
   )
   ```

5. **Lines 188-207** — Replace `_create()` + `sync_to_async` with inline async ORM calls:
   ```python
   # DELETE lines 188-207 (the _create function and its sync_to_async call):
   def _create():
       with transaction.atomic():
           tenant, _ = Tenant.objects.get_or_create(...)
           ...
       return tm
   tm = await sync_to_async(_create)()

   # REPLACE with:
   tenant, _ = await Tenant.objects.aget_or_create(
       provider=provider,
       external_id=tenant_id,
       defaults={"canonical_name": tenant_name},
   )
   tm, _ = await TenantMembership.objects.aget_or_create(user=user, tenant=tenant)
   await TenantCredential.objects.aupdate_or_create(
       tenant_membership=tm,
       defaults={
           "credential_type": TenantCredential.API_KEY,
           "encrypted_credential": encrypted,
       },
   )
   ```

   Also remove the now-unused `from django.db import transaction` import (line 178).

6. **Line 256** — second `verify_commcare_credential` call:
   ```python
   # Change:
   await sync_to_async(verify_commcare_credential)(
       domain=tm.tenant.external_id, username=cc_username, api_key=cc_api_key
   )
   # To:
   await verify_commcare_credential(
       domain=tm.tenant.external_id, username=cc_username, api_key=cc_api_key
   )
   ```

7. **Line 316** — `resolve_connect_opportunities`:
   ```python
   # Change:
   memberships = await sync_to_async(resolve_connect_opportunities)(user, connect_token)
   # To:
   memberships = await resolve_connect_opportunities(user, connect_token)
   ```

- [ ] **Step 2: Run the tenant API and view tests**

Run: `uv run pytest tests/test_tenant_api.py tests/test_tenant_ensure_api.py -v`
Expected: PASS. These tests hit the views through Django test client; since the underlying services are now async, they should work. If any tests fail due to stale `requests` mocking on old import paths, update the mock targets to use `httpx`.

- [ ] **Step 3: Run the full users-related test suite**

Run: `uv run pytest tests/ -k "tenant or oauth or credential or token" -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/users/views.py
git commit -m "feat(users): remove all sync_to_async from views, call async services directly"
```

---

### Task 7: Verify zero `sync_to_async` in `apps/users/` and run full suite

**Files:** None (verification only)

- [ ] **Step 1: Verify no sync_to_async remains in apps/users/**

Run: `grep -rn "sync_to_async\|async_to_sync" apps/users/`
Expected: Only the comment in `apps/users/decorators.py:22` (a docstring mention, not actual usage). Zero functional `sync_to_async` calls remain.

- [ ] **Step 2: Verify no stale `import requests` in converted service files**

Run: `grep -rn "import requests" apps/users/services/`
Expected: No matches. (The provider views in `apps/users/providers/` still use `requests` — that's expected and out of scope.)

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest`
Expected: All tests PASS with no regressions.

- [ ] **Step 4: Run linter**

Run: `uv run ruff check apps/users/services/ apps/users/views.py tests/test_tenant_verification.py tests/test_tenant_resolution.py tests/test_connect_tenant_resolution.py tests/test_oauth_tokens.py`
Expected: Clean (no issues).

- [ ] **Step 5: Final commit (if any lint fixes needed)**

```bash
git add -A && git commit -m "chore: lint fixes for async httpx migration"
```
