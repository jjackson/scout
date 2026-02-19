# Users

Scout uses Django's authentication system with a custom user model that uses email as the primary identifier.

## Authentication methods

### Email and password

Users can log in with email and password via the SPA login form. The login endpoint (`POST /api/auth/login/`) validates credentials and creates a session cookie.

Login is rate-limited: after 5 failed attempts for a given email address, the account is locked out for 5 minutes.

### OAuth providers

Scout supports OAuth login via django-allauth. Built-in providers include:

- **Google** -- sign in with Google accounts.
- **GitHub** -- sign in with GitHub accounts.
- **CommCare** -- sign in with CommCare HQ accounts.
- **CommCare Connect** -- sign in with CommCare Connect accounts.

OAuth credentials (client ID and secret) are configured via the Django admin at `/admin/socialaccount/socialapp/`. OAuth tokens are encrypted at rest and can be refreshed proactively before expiry.

When a user logs in via OAuth for the first time, a Django user is automatically created. If a user with the same email already exists, the social account is linked to the existing user.

## Session management

Scout uses session-cookie authentication (not JWT). Sessions are managed by Django's session framework. The SPA reads the CSRF token from a cookie and includes it in API requests.

Key endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/csrf/` | GET | Set CSRF cookie |
| `/api/auth/me/` | GET | Get current user info |
| `/api/auth/login/` | POST | Email/password login |
| `/api/auth/logout/` | POST | End session |

## Roles

Users are assigned roles per-project through the ProjectMembership model:

| Role | Permissions |
|------|-------------|
| **Viewer** | Chat with the agent and view results |
| **Analyst** | Chat, export data, create saved queries |
| **Admin** | Full project configuration access |

A user can have different roles in different projects.

## Creating users

Users can be created through:

1. **Django admin** -- `/admin/users/user/add/`
2. **`createsuperuser` command** -- `uv run manage.py createsuperuser`
3. **OAuth sign-up** -- first login via Google/GitHub auto-creates the user.
4. **Django allauth sign-up** -- if enabled, users can self-register.

## Superusers

Django superusers have full access to the admin interface and can manage all projects, users, and settings. Create the initial superuser during installation with `uv run manage.py createsuperuser`.
