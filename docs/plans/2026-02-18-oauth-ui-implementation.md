# OAuth UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OAuth login buttons to the login page and a connected accounts management page for post-login provider linking.

**Architecture:** A new `GET /api/auth/providers/` endpoint returns configured OAuth providers (and connection status for authenticated users). The frontend LoginForm renders provider buttons dynamically. A new `/settings/connections` page lets users connect/disconnect providers. Disconnect is guarded: users must keep at least one login method.

**Tech Stack:** Django views + allauth models (backend), React + Zustand + existing UI components (frontend)

---

### Task 1: Backend — providers list endpoint

**Files:**
- Modify: `apps/chat/views.py` (add `providers_view` function)
- Modify: `apps/chat/auth_urls.py` (add route)
- Test: `tests/test_auth.py` (add `TestProvidersEndpoint` class)

**Step 1: Write the failing test**

Add to `tests/test_auth.py`:

```python
@pytest.mark.django_db
class TestProvidersEndpoint:
    """Tests for GET /api/auth/providers/."""

    def test_returns_configured_providers(self, client, google_social_app, github_social_app):
        """Unauthenticated request returns configured providers without connection status."""
        resp = client.get("/api/auth/providers/")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        ids = {p["id"] for p in data["providers"]}
        assert "google" in ids
        assert "github" in ids
        for p in data["providers"]:
            assert "name" in p
            assert "login_url" in p
            assert "connected" not in p  # not authenticated

    def test_returns_empty_when_no_providers(self, client, site):
        """Returns empty list when no SocialApps are configured."""
        resp = client.get("/api/auth/providers/")
        assert resp.status_code == 200
        assert resp.json()["providers"] == []

    def test_includes_connection_status_when_authenticated(
        self, client, user, google_social_app, github_social_app, social_account
    ):
        """Authenticated request includes connected boolean per provider."""
        client.force_login(user)
        resp = client.get("/api/auth/providers/")
        assert resp.status_code == 200
        providers = {p["id"]: p for p in resp.json()["providers"]}
        assert providers["google"]["connected"] is True  # social_account fixture is google
        assert providers["github"]["connected"] is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py::TestProvidersEndpoint -v`
Expected: FAIL — URL not found (404)

**Step 3: Write the endpoint**

In `apps/chat/views.py`, add:

```python
from allauth.socialaccount.models import SocialAccount, SocialApp
from django.contrib.sites.models import Site

PROVIDER_DISPLAY = {
    "google": "Google",
    "github": "GitHub",
    "commcare": "CommCare",
    "commcare_connect": "CommCare Connect",
}

@require_GET
def providers_view(request):
    """Return OAuth providers configured for this site, with connection status if authenticated."""
    current_site = Site.objects.get_current()
    apps = SocialApp.objects.filter(sites=current_site)

    connected_providers = set()
    if request.user.is_authenticated:
        connected_providers = set(
            SocialAccount.objects.filter(user=request.user)
            .values_list("provider", flat=True)
        )

    providers = []
    for app in apps:
        entry = {
            "id": app.provider,
            "name": PROVIDER_DISPLAY.get(app.provider, app.name),
            "login_url": f"/accounts/{app.provider}/login/",
        }
        if request.user.is_authenticated:
            entry["connected"] = app.provider in connected_providers
        providers.append(entry)

    return JsonResponse({"providers": providers})
```

In `apps/chat/auth_urls.py`, add:

```python
from apps.chat.views import csrf_view, login_view, logout_view, me_view, providers_view

urlpatterns = [
    # ... existing paths ...
    path("providers/", providers_view, name="providers"),
]
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth.py::TestProvidersEndpoint -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/chat/views.py apps/chat/auth_urls.py tests/test_auth.py
git commit -m "feat: add GET /api/auth/providers/ endpoint"
```

---

### Task 2: Backend — disconnect endpoint

**Files:**
- Modify: `apps/chat/views.py` (add `disconnect_provider_view`)
- Modify: `apps/chat/auth_urls.py` (add route)
- Test: `tests/test_auth.py` (add `TestDisconnectProvider` class)

**Step 1: Write the failing test**

Add to `tests/test_auth.py`:

```python
@pytest.mark.django_db
class TestDisconnectProvider:
    """Tests for POST /api/auth/providers/<provider>/disconnect/."""

    def test_disconnect_requires_auth(self, client):
        resp = client.post("/api/auth/providers/google/disconnect/")
        assert resp.status_code == 401

    def test_disconnect_existing_provider(self, client, user, social_account):
        """User with password + social account can disconnect the social account."""
        client.force_login(user)
        resp = client.post("/api/auth/providers/google/disconnect/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"
        assert not SocialAccount.objects.filter(user=user, provider="google").exists()

    def test_disconnect_only_login_method_blocked(self, client, user, social_account):
        """Cannot disconnect if it's the only login method (no password)."""
        user.set_unusable_password()
        user.save()
        client.force_login(user)
        resp = client.post("/api/auth/providers/google/disconnect/")
        assert resp.status_code == 400
        assert "only login method" in resp.json()["error"].lower()
        # Social account should still exist
        assert SocialAccount.objects.filter(user=user, provider="google").exists()

    def test_disconnect_allowed_with_other_provider(self, client, user, social_account):
        """Can disconnect one provider if another is still connected."""
        user.set_unusable_password()
        user.save()
        # Add a second social account
        SocialAccount.objects.create(user=user, provider="github", uid="gh_123")
        client.force_login(user)
        resp = client.post("/api/auth/providers/google/disconnect/")
        assert resp.status_code == 200

    def test_disconnect_nonexistent_returns_404(self, client, user):
        client.force_login(user)
        resp = client.post("/api/auth/providers/google/disconnect/")
        assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_auth.py::TestDisconnectProvider -v`
Expected: FAIL — URL not found (404)

**Step 3: Write the endpoint**

In `apps/chat/views.py`, add:

```python
@require_POST
def disconnect_provider_view(request, provider_id):
    """Disconnect a social account. Prevents removing the last login method."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)

    account = SocialAccount.objects.filter(
        user=request.user, provider=provider_id
    ).first()
    if not account:
        return JsonResponse({"error": "Not connected"}, status=404)

    # Guard: must keep at least one login method
    has_password = request.user.has_usable_password()
    other_socials = (
        SocialAccount.objects.filter(user=request.user)
        .exclude(provider=provider_id)
        .exists()
    )
    if not has_password and not other_socials:
        return JsonResponse(
            {"error": "Cannot disconnect your only login method. Set a password first."},
            status=400,
        )

    account.delete()
    return JsonResponse({"status": "disconnected"})
```

In `apps/chat/auth_urls.py`, add the route:

```python
path("providers/<str:provider_id>/disconnect/", disconnect_provider_view, name="disconnect-provider"),
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_auth.py::TestDisconnectProvider -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/chat/views.py apps/chat/auth_urls.py tests/test_auth.py
git commit -m "feat: add POST /api/auth/providers/<id>/disconnect/ endpoint"
```

---

### Task 3: Frontend — add OAuth buttons to LoginForm

**Files:**
- Modify: `frontend/src/components/LoginForm/LoginForm.tsx`

**Step 1: Add provider fetching and OAuth buttons**

Update `LoginForm.tsx` to fetch providers on mount and render buttons below the form:

```tsx
import { useEffect, useState, type FormEvent } from "react"
import { useAppStore } from "@/store/store"
import { api } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface OAuthProvider {
  id: string
  name: string
  login_url: string
}

export function LoginForm() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [providers, setProviders] = useState<OAuthProvider[]>([])
  const authError = useAppStore((s) => s.authError)
  const login = useAppStore((s) => s.authActions.login)

  useEffect(() => {
    api.get<{ providers: OAuthProvider[] }>("/api/auth/providers/")
      .then((data) => setProviders(data.providers))
      .catch(() => {})  // silently ignore — just won't show OAuth buttons
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
    } catch {
      // error is set in the store
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Scout</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* ... existing email/password fields unchanged ... */}
            {authError && (
              <p className="text-sm text-destructive">{authError}</p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          {providers.length > 0 && (
            <>
              <div className="relative my-4">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">
                    or continue with
                  </span>
                </div>
              </div>
              <div className="grid gap-2">
                {providers.map((provider) => (
                  <Button
                    key={provider.id}
                    variant="outline"
                    className="w-full"
                    data-testid={`oauth-login-${provider.id}`}
                    asChild
                  >
                    <a href={`${provider.login_url}?next=/`}>
                      {provider.name}
                    </a>
                  </Button>
                ))}
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
```

**Step 2: Verify manually**

Run: `cd frontend && bun dev`
Visit: `http://localhost:5173` — should see OAuth buttons if providers are configured in Django admin, or just the email/password form if none are configured.

**Step 3: Commit**

```bash
git add frontend/src/components/LoginForm/LoginForm.tsx
git commit -m "feat: add dynamic OAuth login buttons to LoginForm"
```

---

### Task 4: Frontend — ConnectionsPage

**Files:**
- Create: `frontend/src/pages/ConnectionsPage/ConnectionsPage.tsx`
- Create: `frontend/src/pages/ConnectionsPage/index.ts`

**Step 1: Create the page component**

`frontend/src/pages/ConnectionsPage/ConnectionsPage.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react"
import { api } from "@/api/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface Provider {
  id: string
  name: string
  login_url: string
  connected: boolean
}

export function ConnectionsPage() {
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState<string | null>(null)

  const fetchProviders = useCallback(async () => {
    try {
      const data = await api.get<{ providers: Provider[] }>("/api/auth/providers/")
      setProviders(data.providers)
    } catch {
      setError("Failed to load providers")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchProviders() }, [fetchProviders])

  async function handleDisconnect(providerId: string) {
    setDisconnecting(providerId)
    setError(null)
    try {
      await api.post(`/api/auth/providers/${providerId}/disconnect/`)
      await fetchProviders()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to disconnect")
    } finally {
      setDisconnecting(null)
    }
  }

  const connectedCount = providers.filter((p) => p.connected).length

  if (loading) {
    return <div className="p-6 text-muted-foreground">Loading...</div>
  }

  return (
    <div className="mx-auto max-w-lg p-6">
      <h1 className="text-2xl font-semibold mb-1">Connected Accounts</h1>
      <p className="text-sm text-muted-foreground mb-6">
        Manage your linked authentication and data providers.
      </p>

      {error && (
        <p className="text-sm text-destructive mb-4" data-testid="connections-error">
          {error}
        </p>
      )}

      {providers.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No OAuth providers are configured for this deployment.
        </p>
      ) : (
        <div className="space-y-3">
          {providers.map((provider) => (
            <Card key={provider.id}>
              <CardContent className="flex items-center justify-between py-4">
                <div>
                  <p className="font-medium">{provider.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {provider.connected ? "Connected" : "Not connected"}
                  </p>
                </div>
                {provider.connected ? (
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid={`disconnect-${provider.id}`}
                    disabled={disconnecting === provider.id}
                    onClick={() => handleDisconnect(provider.id)}
                  >
                    {disconnecting === provider.id ? "Disconnecting..." : "Disconnect"}
                  </Button>
                ) : (
                  <Button
                    variant="default"
                    size="sm"
                    data-testid={`connect-${provider.id}`}
                    asChild
                  >
                    <a href={`${provider.login_url}?process=connect&next=/settings/connections`}>
                      Connect
                    </a>
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
```

`frontend/src/pages/ConnectionsPage/index.ts`:

```ts
export { ConnectionsPage } from "./ConnectionsPage"
```

**Step 2: Verify the files were created**

Run: `ls frontend/src/pages/ConnectionsPage/`
Expected: `ConnectionsPage.tsx  index.ts`

**Step 3: Commit**

```bash
git add frontend/src/pages/ConnectionsPage/
git commit -m "feat: add ConnectionsPage for managing OAuth providers"
```

---

### Task 5: Frontend — wire up route and sidebar link

**Files:**
- Modify: `frontend/src/router.tsx` (add `/settings/connections` route)
- Modify: `frontend/src/components/Sidebar/Sidebar.tsx` (add link)

**Step 1: Add the route**

In `frontend/src/router.tsx`, add import and route:

```tsx
import { ConnectionsPage } from "@/pages/ConnectionsPage"

// Inside the children array, add:
{ path: "settings/connections", element: <ConnectionsPage /> },
```

**Step 2: Add sidebar link**

In `frontend/src/components/Sidebar/Sidebar.tsx`:

1. Add `Link2` import from lucide-react (for the connected accounts icon).
2. In the User Section (between the email display and the logout button), add:

```tsx
<Link
  to="/settings/connections"
  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
  data-testid="sidebar-connections"
>
  <Link2 className="h-4 w-4" />
  Connected Accounts
</Link>
```

**Step 3: Verify manually**

Run: `cd frontend && bun dev`
- Sidebar should show "Connected Accounts" link above Logout
- Clicking it navigates to `/settings/connections`
- Page shows providers with connect/disconnect buttons

**Step 4: Run lint**

Run: `cd frontend && bun run lint`
Expected: No errors

**Step 5: Commit**

```bash
git add frontend/src/router.tsx frontend/src/components/Sidebar/Sidebar.tsx
git commit -m "feat: wire ConnectionsPage route and sidebar link"
```

---

### Task 6: Backend tests — run full suite

**Step 1: Run all backend tests**

Run: `uv run pytest -v`
Expected: All tests pass, including new `TestProvidersEndpoint` and `TestDisconnectProvider`.

**Step 2: Run lint**

Run: `uv run ruff check .`
Expected: No errors

**Step 3: Run format check**

Run: `uv run ruff format --check .`
Expected: No formatting issues (or run `uv run ruff format .` to fix)

---

### Task 7: Final commit and push

**Step 1: Verify all changes**

Run: `git status` and `git diff --stat`
Ensure only expected files are modified.

**Step 2: Push**

Run: `git push`
