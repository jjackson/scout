# Scout - Data Agent Platform

A self-hosted platform for deploying AI agents that can query project-specific PostgreSQL databases. Each project gets an isolated agent with its own system prompt, database access scope, and auto-generated data dictionary.

## Features

- **Project Isolation**: Each project connects to its own database with encrypted credentials
- **Knowledge Layer**: Table metadata, canonical metrics, verified queries, business rules
- **Self-Learning**: Agent learns from errors and applies corrections to future queries
- **Rich Artifacts**: Interactive dashboards, charts, and reports via sandboxed React components
- **Recipe System**: Save and replay successful analysis workflows
- **Multi-Provider OAuth**: Supports Google, GitHub, and custom OAuth providers

## Quick Start

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

## Development with Docker

```bash
docker compose up
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Chainlit Frontend                      │
│  (Auth, Project Selection, Chat, Artifact Rendering)     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  Django Backend (API)                     │
│  (Project CRUD, User Management, Agent Config, Auth)     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│               LangGraph Agent Runtime                    │
│  - Knowledge-grounded SQL generation                     │
│  - Self-correction loop                                  │
│  - Artifact creation                                     │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│          PostgreSQL (per-project isolation)               │
└─────────────────────────────────────────────────────────┘
```

## License

Proprietary - All rights reserved.
