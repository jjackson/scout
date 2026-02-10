# Sharing

Share artifacts with teammates, stakeholders, or external users via secure share links.

## Access levels

Each share link has an access level that controls who can view the artifact:

| Level | Who can view |
|-------|-------------|
| **Public** | Anyone with the link, no login required |
| **Project** | Only members of the artifact's project (must be logged in) |
| **Specific** | Only explicitly named users (must be logged in) |

The default access level is **Project**.

## Creating a share link

Create a share link via the API:

```
POST /api/artifacts/<artifact_id>/share/
```

Request body:

```json
{
  "access_level": "public",
  "expires_at": "2026-03-01T00:00:00Z"
}
```

The response includes a `share_token` that forms the share URL:

```
/api/artifacts/shared/<share_token>/
```

## Expiration

Share links can have an optional expiration date. After expiration, the link returns a 403 error. Links without an expiration date remain active indefinitely.

## Managing share links

**List all share links for an artifact:**

```
GET /api/artifacts/<artifact_id>/shares/
```

**Revoke a share link:**

```
DELETE /api/artifacts/<artifact_id>/shares/<share_token>/
```

Revoking a share link immediately disables access through that link.

## View tracking

Each share link tracks how many times it has been viewed. This count is visible when listing share links.
