# Configuration

Scout is configured via environment variables, typically set in a `.env` file in the project root.

## Required variables

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret key for cryptographic signing. Must be unique and secret in production. |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude. Starts with `sk-ant-`. |
| `DB_CREDENTIAL_KEY` | Fernet key for encrypting project database credentials at rest. Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | PostgreSQL connection URL for Scout's own database. Example: `postgresql://user:pass@localhost/scout` |

## Optional variables

### Django

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DEBUG` | `True` | Enable debug mode. Set to `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed host headers. |
| `DJANGO_SETTINGS_MODULE` | -- | Settings module to use. Options: `config.settings.development`, `config.settings.production`, `config.settings.test` |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173` | Comma-separated list of trusted origins for CSRF. Set to your frontend's URL in production. |

### Cache

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | (empty) | Redis connection URL. If set, Redis is used for caching. Otherwise, local memory cache is used. |

### MCP Server

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_URL` | `http://localhost:8100/mcp` | URL of the MCP server for tool-based data access. |

### Rate limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONNECTIONS_PER_PROJECT` | `5` | Maximum concurrent database connections per project. |
| `MAX_QUERIES_PER_MINUTE` | `60` | Maximum queries per minute per user. |

### LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (empty) | Anthropic API key. Required for the agent to function. |

The default LLM model (`claude-sonnet-4-5-20250929`) can be overridden per-project in the project settings.

### Header-based authentication

For deployments behind a reverse proxy that handles authentication (e.g., OAuth2 Proxy):

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTH_USER_ID_HEADER` | (empty) | HTTP header containing the authenticated user ID. |
| `AUTH_USER_EMAIL_HEADER` | (empty) | HTTP header containing the authenticated user email. |
| `AUTH_USER_NAME_HEADER` | (empty) | HTTP header containing the authenticated user name. |

## Frontend environment

The frontend uses Vite and proxies API requests to the backend in development. No frontend-specific environment variables are required for development. For production builds, the frontend is served as static files and API requests are routed by the reverse proxy.
