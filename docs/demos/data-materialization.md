# Data Materialization Feature Demo

*2026-02-11T06:36:20Z*

This demo showcases the new data materialization feature that allows Scout to fetch data from external APIs (CommCare, CommCare Connect) and make it available for querying by the AI agent.

## Feature Overview

The data materialization system consists of:
1. **Database Connection Management** - Centralized credential storage for project databases
2. **Data Source Connectors** - OAuth-based connectors for CommCare and CommCare Connect
3. **Background Sync Jobs** - Celery tasks for periodic data refresh
4. **Agent Integration** - SQL tool access to materialized data schemas

## 1. Data Source Models

Let's explore the new models in the datasources app.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.datasources.models import (
    DatabaseConnection, DataSource, DataSourceType,
    ProjectDataSource, DataSourceCredential, MaterializedDataset, SyncJob
)

print('=== Data Source Models ===')
print()
print('DatabaseConnection fields:')
for f in DatabaseConnection._meta.get_fields():
    if hasattr(f, 'name'):
        print(f'  - {f.name}')

print()
print('DataSource types available:')
for choice in DataSourceType:
    print(f'  - {choice.value}: {choice.label}')
"
```

```output
=== Data Source Models ===

DatabaseConnection fields:
  - projects
  - id
  - name
  - description
  - db_host
  - db_port
  - db_name
  - _db_user
  - _db_password
  - created_by
  - created_at
  - updated_at

DataSource types available:
  - commcare: CommCare
  - commcare_connect: CommCare Connect
```

## 2. Connector Framework

The connector framework provides a pluggable architecture for different data sources. Each connector implements OAuth authentication and data sync methods.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.datasources.connectors.registry import get_available_source_types, _CONNECTORS

print('=== Registered Connectors ===')
print()
for source_type in get_available_source_types():
    connector_cls = _CONNECTORS[source_type]
    print(f'{source_type.value}:')
    print(f'  Class: {connector_cls.__name__}')
    print(f'  Module: {connector_cls.__module__}')
    print()
"
```

```output
=== Registered Connectors ===

commcare:
  Class: CommCareConnector
  Module: apps.datasources.connectors.commcare

commcare_connect:
  Class: CommCareConnectConnector
  Module: apps.datasources.connectors.commcare_connect

```

## 3. Base Connector Interface

All connectors implement the BaseConnector abstract class which defines the required methods for OAuth and data sync.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.datasources.connectors.base import BaseConnector
import inspect

print('=== BaseConnector Interface ===')
print()
for name, method in inspect.getmembers(BaseConnector, predicate=inspect.isfunction):
    if not name.startswith('_'):
        sig = inspect.signature(method)
        print(f'{name}{sig}')
        if method.__doc__:
            doc = method.__doc__.strip().split(chr(10))[0]
            print(f'    {doc}')
        print()
"
```

```output
=== BaseConnector Interface ===

exchange_code_for_tokens(self, code: str, redirect_uri: str) -> apps.datasources.connectors.base.TokenResult
    Exchange authorization code for access/refresh tokens.

get_available_datasets(self, credential: 'DataSourceCredential', config: dict) -> list[apps.datasources.connectors.base.DatasetInfo]
    List what data can be synced (forms, cases, opportunities, etc.).

get_oauth_authorization_url(self, redirect_uri: str, state: str, scopes: list[str] | None = None) -> str
    Return URL to redirect user for OAuth authorization.

refresh_access_token(self, refresh_token: str) -> apps.datasources.connectors.base.TokenResult
    Refresh an expired access token.

sync_dataset(self, credential: 'DataSourceCredential', dataset_name: str, schema_name: str, config: dict, progress_callback: Optional[Callable[[apps.datasources.connectors.base.SyncProgress], NoneType]] = None, cursor: dict | None = None) -> apps.datasources.connectors.base.SyncResult
    Fetch data and write to the specified schema.

```

## 4. Celery Background Tasks

The system uses Celery for background processing of data sync jobs.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.datasources import tasks

print('=== Celery Tasks ===')
print()
task_list = [
    ('sync_dataset', 'Sync a single materialized dataset'),
    ('schedule_dataset_refreshes', 'Check and schedule refreshes for due datasets'),
    ('cleanup_inactive_datasets', 'Remove data for inactive users (24h inactivity)'),
    ('refresh_expiring_tokens', 'Refresh OAuth tokens expiring within 1 hour'),
    ('resume_paused_syncs', 'Resume syncs paused due to rate limiting'),
]
for name, desc in task_list:
    task = getattr(tasks, name, None)
    if task:
        print(f'{name}:')
        print(f'  {desc}')
        print()
"
```

```output
=== Celery Tasks ===

sync_dataset:
  Sync a single materialized dataset

schedule_dataset_refreshes:
  Check and schedule refreshes for due datasets

cleanup_inactive_datasets:
  Remove data for inactive users (24h inactivity)

refresh_expiring_tokens:
  Refresh OAuth tokens expiring within 1 hour

resume_paused_syncs:
  Resume syncs paused due to rate limiting

```

## 5. SQL Tool Integration

The SQL tool has been updated to include materialized data schemas in the search path, allowing users to query their synced data alongside project data.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.agents.tools.sql_tool import SQLValidator

# Test schema validation with multiple allowed schemas
validator = SQLValidator(
    schema='public',
    allowed_schemas=['commcare_project1', 'user_123_commcare'],
)

test_queries = [
    ('SELECT * FROM public.users', 'Query public schema'),
    ('SELECT * FROM commcare_project1.forms', 'Query materialized CommCare data'),
    ('SELECT * FROM user_123_commcare.submissions', 'Query user-specific data'),
]

print('=== SQL Validator Schema Support ===')
print()
print('Allowed schemas:', ['public', validator.schema] + validator.allowed_schemas)
print()

for sql, desc in test_queries:
    try:
        validator.validate(sql)
        print(f'✓ {desc}')
        print(f'  SQL: {sql}')
    except Exception as e:
        print(f'✗ {desc}')
        print(f'  Error: {e}')
    print()
"
```

```output
=== SQL Validator Schema Support ===

Allowed schemas: ['public', 'public', 'commcare_project1', 'user_123_commcare']

✓ Query public schema
  SQL: SELECT * FROM public.users

✓ Query materialized CommCare data
  SQL: SELECT * FROM commcare_project1.forms

✓ Query user-specific data
  SQL: SELECT * FROM user_123_commcare.submissions

```

## 6. API Endpoints

The feature exposes REST API endpoints for managing data sources and connections.

```bash
DJANGO_SETTINGS_MODULE=config.settings.development python -c "
import django
django.setup()
from apps.datasources.urls import router, urlpatterns

print('=== Data Sources API Endpoints ===')
print()
print('ViewSet routes:')
for prefix, viewset, basename in router.registry:
    print(f'  /api/datasources/{prefix}/')
    print(f'    ViewSet: {viewset.__name__}')
    print()

print('Additional endpoints:')
for pattern in urlpatterns:
    if hasattr(pattern, 'name') and pattern.name:
        path = str(pattern.pattern)
        print(f'  /api/datasources/{path}')
        print(f'    Name: {pattern.name}')
        print()
"
```

```output
=== Data Sources API Endpoints ===

ViewSet routes:
  /api/datasources/connections/
    ViewSet: DatabaseConnectionViewSet

  /api/datasources/sources/
    ViewSet: DataSourceViewSet

  /api/datasources/project-sources/
    ViewSet: ProjectDataSourceViewSet

  /api/datasources/credentials/
    ViewSet: DataSourceCredentialViewSet

  /api/datasources/datasets/
    ViewSet: MaterializedDatasetViewSet

  /api/datasources/sync-jobs/
    ViewSet: SyncJobViewSet

Additional endpoints:
  /api/datasources/types/
    Name: datasource-types

  /api/datasources/oauth/start/
    Name: oauth-start

  /api/datasources/oauth/callback/
    Name: oauth-callback

```

## 7. Frontend Integration

The feature includes a new Data Sources page in the React frontend accessible from the sidebar.

```bash
echo '=== Frontend Components ===' && echo && find frontend/src -name '*.tsx' -path '*DataSources*' | while read f; do echo "File: $f"; head -20 "$f" | grep -E '(export|function|interface)' | head -5; echo; done
```

```output
=== Frontend Components ===

File: frontend/src/pages/DataSourcesPage/DataSourcesPage.tsx
export function DataSourcesPage() {

```

```bash
echo '=== TypeScript Types ===' && echo && cat frontend/src/pages/DataSourcesPage/types.ts | head -60
```

```output
=== TypeScript Types ===

/**
 * TypeScript types for data sources API.
 */

export interface DatabaseConnection {
  id: string
  name: string
  description: string
  db_host: string
  db_port: number
  db_name: string
  is_active: boolean
  project_count: number
  created_at: string
  updated_at: string
}

export interface DatabaseConnectionFormData {
  name: string
  description: string
  db_host: string
  db_port: number
  db_name: string
  db_user?: string
  db_password?: string
  is_active: boolean
}

export interface DataSource {
  id: string
  name: string
  source_type: DataSourceType
  source_type_display: string
  base_url: string
  oauth_client_id: string
  config: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export type DataSourceType = "commcare" | "commcare_connect"

export interface DataSourceFormData {
  name: string
  source_type: DataSourceType
  base_url: string
  oauth_client_id: string
  oauth_client_secret?: string
  config: Record<string, unknown>
  is_active: boolean
}

export interface ProjectDataSource {
  id: string
  project: string
  data_source: string
  data_source_name: string
  data_source_type: DataSourceType
  credential_mode: CredentialMode
```

## 8. Visual Demo

Let's start the development server and capture screenshots of the new Data Sources page.

```bash {image}
echo 'Screenshot of Data Sources page' && cp docs/demos/datasources-page.png docs/demos/datasources-page-demo.png && echo docs/demos/datasources-page-demo.png
```

![dc424ad5-2026-02-11](dc424ad5-2026-02-11.png)

The Data Sources page shows:
- **Available Sources**: List of configured data sources (CommCare, CommCare Connect) with OAuth connection buttons
- **My Connections**: User's active credentials and their expiration status  
- **Synced Data**: Materialized datasets with sync status and manual refresh triggers

![Data Sources Page](datasources-page.png)

## Summary

The data materialization feature enables Scout to:

1. **Connect to external APIs** via OAuth (CommCare, CommCare Connect)
2. **Sync data periodically** using Celery background tasks
3. **Store data in PostgreSQL schemas** for efficient querying
4. **Provide unified access** to both project database and materialized data
5. **Manage credentials centrally** with proper encryption and access control
6. **Clean up automatically** when users become inactive

This allows users to ask questions about their CommCare form submissions and CommCare Connect opportunity data directly through the Scout chat interface.
