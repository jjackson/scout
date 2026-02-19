# Docker deployment

The simplest way to deploy Scout is with Docker Compose, which starts all services together.

## Quick start

```bash
docker compose up --build
```

This starts five services:

| Service | Port | Description |
|---------|------|-------------|
| Backend (api) | 8000 | Django ASGI server via uvicorn |
| Frontend | 3000 | React app served via nginx |
| MCP Server | 8100 | Model Context Protocol server for data access |
| PostgreSQL | 5432 | Scout's internal database |
| Redis | 6379 | Caching, rate limiting, and Celery broker |

## Configuration

Create a `.env` file in the project root with the required environment variables before running `docker compose up`. See [Configuration](configuration.md) for the full reference.

At minimum:

```
DJANGO_SECRET_KEY=your-secret-key
ANTHROPIC_API_KEY=sk-ant-...
DB_CREDENTIAL_KEY=your-fernet-key
DATABASE_URL=postgresql://scout:scout@db:5432/scout
```

## Persistent data

The PostgreSQL data directory is mounted as a Docker volume to persist data across container restarts. Conversation history (stored via the PostgreSQL checkpointer) and all project configuration survive restarts.

## Health check

The backend exposes a health check endpoint at `/health/` that returns `{"status": "ok"}`. Use this for Docker health checks and load balancer probes.

## Production considerations

- Set `DJANGO_DEBUG=False` in production.
- Set `DJANGO_ALLOWED_HOSTS` to your domain name(s).
- Set `CSRF_TRUSTED_ORIGINS` to your frontend's origin.
- Use a strong, unique `DJANGO_SECRET_KEY`.
- Consider placing a reverse proxy (nginx, Caddy) in front for TLS termination.
- Set `MCP_SERVER_URL` if the MCP server runs on a different host (defaults to `http://localhost:8100/mcp`).
