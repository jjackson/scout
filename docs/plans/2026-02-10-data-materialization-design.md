# Data Materialization & Credential Management Design

**Date:** 2026-02-10  
**Status:** Draft

## Overview

This design addresses two related requirements:

1. **Centralized Database Credentials** - Decouple database connection credentials from the Project model to enable sharing across projects and separation of concerns (DBAs manage credentials, project admins assign them).

2. **Data Materialization from APIs** - Fetch data from external APIs (CommCare, CommCare Connect) and materialize it into the local PostgreSQL database so the agent can query it.

## Goals

- Multiple projects can share the same database connection
- DBAs can manage credentials without project admins seeing raw passwords
- Support both project-level (shared) and user-level (individual) API credentials
- Data isolation: project credentials share a schema, user credentials get separate schemas
- Automatic daily refresh for active users
- Automatic cleanup after 24 hours of inactivity
- Extensible connector framework for adding new data sources

## Non-Goals

- Real-time data sync (batch/periodic only)
- Bi-directional sync (read-only from external APIs)
- Data transformation beyond what connectors provide

---

## Part 1: Centralized Database Credentials

### Problem

Currently, database credentials are embedded in the Project model. This causes issues when:
- Multiple projects need to connect to the same database (different schemas)
- DBAs should manage credentials without project admins seeing raw passwords

### Solution: DatabaseConnection Model

#### Model Definition

```python
class DatabaseConnection(models.Model):
    """
    Centralized storage for database connection credentials.
    Multiple projects can reference the same connection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)  # e.g., "Production Analytics DB"
    description = models.TextField(blank=True)
    
    # Connection details
    db_host = models.CharField(max_length=255)
    db_port = models.IntegerField(default=5432)
    db_name = models.CharField(max_length=255)
    
    # Encrypted credentials
    _db_user = models.BinaryField(db_column="db_user")
    _db_password = models.BinaryField(db_column="db_password")
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_database_connections",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("manage_database_connections", "Can create and edit database connections"),
        ]
```

#### Project Model Changes

```python
class Project(models.Model):
    # ... existing fields ...
    
    # NEW: Reference to shared connection
    database_connection = models.ForeignKey(
        DatabaseConnection,
        on_delete=models.PROTECT,
        related_name="projects",
    )
    
    # KEEP: Schema stays on project (each project can use different schema)
    db_schema = models.CharField(max_length=255, default="public")
    
    # REMOVE: db_host, db_port, db_name, _db_user, _db_password
```

#### Access Control

- New permission: `manage_database_connections`
- Users with this permission can create/edit/delete connections
- Project admins can assign a connection to their project but cannot view raw credentials
- API returns connection name/host but never the password

#### Migration Strategy

1. Create `DatabaseConnection` model
2. Migrate existing Project credentials to DatabaseConnection records
3. Add `database_connection` FK to Project
4. Remove credential fields from Project

---

## Part 2: Data Source Connectors

### Problem

Scout needs to fetch data from external APIs (CommCare, CommCare Connect) and materialize it into the local database for the agent to query.

### Data Sources

**Initial support:**
- **CommCare** - Forms, cases, users via commcarehq.org API
- **CommCare Connect** - Opportunities, visits, payments, users via commcare-connect.org API

Both use OAuth 2.0 for authentication.

### Models

#### DataSource

```python
class DataSourceType(models.TextChoices):
    COMMCARE = "commcare", "CommCare"
    COMMCARE_CONNECT = "commcare_connect", "CommCare Connect"


class DataSource(models.Model):
    """
    A configured external data source (e.g., CommCare production instance).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)  # e.g., "CommCare Production"
    source_type = models.CharField(max_length=50, choices=DataSourceType.choices)
    base_url = models.URLField()  # e.g., "https://www.commcarehq.org"
    
    # Source-specific configuration
    config = models.JSONField(default=dict, blank=True)
    # CommCare: {"domain": "my-project", "app_id": "abc123"}
    # Connect: {"org_slug": "my-org"}
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### ProjectDataSource

```python
class CredentialMode(models.TextChoices):
    PROJECT = "project", "Project-level"  # Service credentials, shared data
    USER = "user", "User-level"  # Each user authenticates, isolated data


class ProjectDataSource(models.Model):
    """
    Links a project to a data source with sync configuration.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="project_data_sources",
    )
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="project_links",
    )
    
    credential_mode = models.CharField(
        max_length=20,
        choices=CredentialMode.choices,
        default=CredentialMode.USER,
    )
    
    # What to sync
    sync_config = models.JSONField(default=dict, blank=True)
    # CommCare: {"datasets": ["forms"], "form_xmlns": ["http://..."]}
    # Connect: {"datasets": ["opportunities", "visits"]}
    
    refresh_interval_hours = models.IntegerField(default=24)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["project", "data_source"]
```

#### DataSourceCredential

```python
class DataSourceCredential(models.Model):
    """
    OAuth tokens for accessing a data source.
    Either project-level (shared) or user-level (individual).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="credentials",
    )
    
    # One of these must be set
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_source_credentials",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_source_credentials",
    )
    
    # Encrypted tokens
    _access_token = models.BinaryField()
    _refresh_token = models.BinaryField()
    token_expires_at = models.DateTimeField()
    
    # OAuth metadata
    scopes = models.JSONField(default=list)
    external_user_id = models.CharField(max_length=255, blank=True)
    
    # Status
    is_valid = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(project__isnull=False, user__isnull=True) |
                    models.Q(project__isnull=True, user__isnull=False)
                ),
                name="credential_project_xor_user",
            ),
        ]
        unique_together = [
            ("data_source", "project"),
            ("data_source", "user"),
        ]
```

---

## Part 3: Materialized Data & Schema Isolation

### Problem

Data fetched from APIs needs to be stored in isolated schemas, with different isolation depending on credential mode.

### MaterializedDataset Model

```python
class DatasetStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SYNCING = "syncing", "Syncing"
    READY = "ready", "Ready"
    ERROR = "error", "Error"
    EXPIRED = "expired", "Expired"


class MaterializedDataset(models.Model):
    """
    Tracks a materialized dataset in a PostgreSQL schema.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_data_source = models.ForeignKey(
        ProjectDataSource,
        on_delete=models.CASCADE,
        related_name="materialized_datasets",
    )
    
    # Set for user-level credential mode, null for project-level
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="materialized_datasets",
    )
    
    schema_name = models.CharField(max_length=63)  # PostgreSQL identifier limit
    status = models.CharField(
        max_length=20,
        choices=DatasetStatus.choices,
        default=DatasetStatus.PENDING,
    )
    
    # Sync tracking
    last_sync_at = models.DateTimeField(null=True, blank=True)
    next_sync_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)
    row_counts = models.JSONField(default=dict)  # {"forms": 1500, "cases": 300}
    
    # Activity tracking for cleanup
    last_activity_at = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["project_data_source", "user"]
```

### SyncJob Model

```python
class SyncJobStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class SyncJob(models.Model):
    """
    Tracks individual sync operations for debugging and progress.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    materialized_dataset = models.ForeignKey(
        MaterializedDataset,
        on_delete=models.CASCADE,
        related_name="sync_jobs",
    )
    
    status = models.CharField(
        max_length=20,
        choices=SyncJobStatus.choices,
        default=SyncJobStatus.QUEUED,
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    progress = models.JSONField(default=dict)  # {"forms": {"fetched": 500, "total": 1500}}
    error_message = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Schema Naming Convention

- Project-level: `data_{project_id_short}_{source_type}` (e.g., `data_abc123_commcare`)
- User-level: `data_{user_id_short}_{source_type}` (e.g., `data_usr456_commcare`)

---

## Part 4: Connector Framework

### Abstract Base Connector

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable


@dataclass
class TokenResult:
    access_token: str
    refresh_token: str
    expires_at: datetime
    scopes: list[str]
    external_user_id: str | None = None


@dataclass
class DatasetInfo:
    name: str  # e.g., "forms", "cases"
    description: str
    estimated_rows: int | None = None


@dataclass
class SyncResult:
    success: bool
    rows_synced: dict[str, int]  # {"forms": 1500}
    error: str | None = None


class BaseConnector(ABC):
    """Abstract base for all data source connectors."""
    
    source_type: DataSourceType
    
    @abstractmethod
    def get_oauth_authorization_url(
        self, 
        redirect_uri: str, 
        state: str,
        scopes: list[str] | None = None,
    ) -> str:
        """Return URL to redirect user for OAuth authorization."""
        pass
        
    @abstractmethod
    def exchange_code_for_tokens(
        self, 
        code: str, 
        redirect_uri: str,
    ) -> TokenResult:
        """Exchange authorization code for access/refresh tokens."""
        pass
        
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> TokenResult:
        """Refresh an expired access token."""
        pass
        
    @abstractmethod
    def get_available_datasets(
        self, 
        credential: DataSourceCredential,
        config: dict,
    ) -> list[DatasetInfo]:
        """List what data can be synced (forms, cases, opportunities, etc.)."""
        pass
        
    @abstractmethod
    def sync_dataset(
        self, 
        credential: DataSourceCredential,
        dataset_name: str,
        schema_name: str,
        config: dict,
        progress_callback: Callable[[dict], None],
    ) -> SyncResult:
        """Fetch data and write to the specified schema."""
        pass
```

### Initial Connectors

```
apps/datasources/
├── __init__.py
├── models.py           # DataSource, ProjectDataSource, etc.
├── connectors/
│   ├── __init__.py
│   ├── base.py         # BaseConnector ABC
│   ├── commcare.py     # CommCareConnector
│   └── commcare_connect.py  # CommCareConnectConnector
├── tasks.py            # Celery tasks
├── api/
│   ├── views.py
│   └── serializers.py
└── services/
    ├── sync.py         # Sync orchestration
    └── schema.py       # Schema management
```

---

## Part 5: Background Jobs

### Celery Tasks

```python
# apps/datasources/tasks.py

@shared_task
def sync_dataset(materialized_dataset_id: str):
    """
    Fetch data from API and write to schema.
    """
    dataset = MaterializedDataset.objects.get(id=materialized_dataset_id)
    pds = dataset.project_data_source
    
    # Get appropriate credential
    if pds.credential_mode == CredentialMode.PROJECT:
        credential = DataSourceCredential.objects.get(
            data_source=pds.data_source,
            project=pds.project,
        )
    else:
        credential = DataSourceCredential.objects.get(
            data_source=pds.data_source,
            user=dataset.user,
        )
    
    # Get connector
    connector = get_connector(pds.data_source.source_type)
    
    # Create sync job
    job = SyncJob.objects.create(
        materialized_dataset=dataset,
        status=SyncJobStatus.RUNNING,
        started_at=timezone.now(),
    )
    
    try:
        dataset.status = DatasetStatus.SYNCING
        dataset.save()
        
        # Run sync
        result = connector.sync_dataset(
            credential=credential,
            dataset_name=pds.sync_config.get("datasets", ["forms"])[0],
            schema_name=dataset.schema_name,
            config=pds.data_source.config | pds.sync_config,
            progress_callback=lambda p: update_job_progress(job.id, p),
        )
        
        if result.success:
            dataset.status = DatasetStatus.READY
            dataset.last_sync_at = timezone.now()
            dataset.next_sync_at = timezone.now() + timedelta(hours=pds.refresh_interval_hours)
            dataset.row_counts = result.rows_synced
            dataset.sync_error = ""
            job.status = SyncJobStatus.COMPLETED
        else:
            dataset.status = DatasetStatus.ERROR
            dataset.sync_error = result.error
            job.status = SyncJobStatus.FAILED
            job.error_message = result.error
            
    except Exception as e:
        dataset.status = DatasetStatus.ERROR
        dataset.sync_error = str(e)
        job.status = SyncJobStatus.FAILED
        job.error_message = str(e)
        raise
    finally:
        job.completed_at = timezone.now()
        job.save()
        dataset.save()


@shared_task
def schedule_dataset_refreshes():
    """
    Periodic task (hourly) to queue refreshes for due datasets.
    """
    due_datasets = MaterializedDataset.objects.filter(
        status=DatasetStatus.READY,
        next_sync_at__lte=timezone.now(),
        project_data_source__is_active=True,
    )
    
    for dataset in due_datasets:
        sync_dataset.delay(str(dataset.id))


@shared_task
def cleanup_inactive_datasets():
    """
    Periodic task (hourly) to drop schemas for inactive datasets.
    """
    cutoff = timezone.now() - timedelta(hours=24)
    
    inactive = MaterializedDataset.objects.filter(
        status=DatasetStatus.READY,
        last_activity_at__lt=cutoff,
    )
    
    for dataset in inactive:
        drop_schema(dataset.schema_name)
        dataset.status = DatasetStatus.EXPIRED
        dataset.save()


@shared_task
def refresh_expiring_tokens():
    """
    Periodic task (every 15 min) to refresh tokens expiring soon.
    """
    expiring_soon = timezone.now() + timedelta(hours=1)
    
    credentials = DataSourceCredential.objects.filter(
        is_valid=True,
        token_expires_at__lte=expiring_soon,
    )
    
    for credential in credentials:
        try:
            connector = get_connector(credential.data_source.source_type)
            result = connector.refresh_access_token(credential.refresh_token)
            
            credential.access_token = result.access_token
            credential.refresh_token = result.refresh_token
            credential.token_expires_at = result.expires_at
            credential.save()
        except Exception as e:
            credential.is_valid = False
            credential.save()
            # TODO: Notify user/admin
```

### Celery Beat Schedule

```python
# scout/celery.py

app.conf.beat_schedule = {
    'schedule-dataset-refreshes': {
        'task': 'apps.datasources.tasks.schedule_dataset_refreshes',
        'schedule': crontab(minute=0),  # Every hour
    },
    'cleanup-inactive-datasets': {
        'task': 'apps.datasources.tasks.cleanup_inactive_datasets',
        'schedule': crontab(minute=15),  # Every hour at :15
    },
    'refresh-expiring-tokens': {
        'task': 'apps.datasources.tasks.refresh_expiring_tokens',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}
```

---

## Part 6: API Endpoints

### OAuth Flow

```
1. User/Admin initiates connection:
   POST /api/projects/{pid}/data-sources/{id}/authorize/
   Response: { "authorization_url": "https://commcarehq.org/oauth/authorize?..." }

2. User completes OAuth in browser, redirected to:
   GET /api/oauth/callback/{source_type}/?code=...&state=...
   
3. Backend exchanges code for tokens, stores credential, redirects to frontend
```

### Endpoints

```
Database Connections (DBA):
  GET    /api/database-connections/              # List connections
  POST   /api/database-connections/              # Create connection
  GET    /api/database-connections/{id}/         # Get details (no password)
  PATCH  /api/database-connections/{id}/         # Update
  DELETE /api/database-connections/{id}/         # Delete

Data Sources (admin):
  GET    /api/data-sources/                      # List configured sources
  POST   /api/data-sources/                      # Create source
  GET    /api/data-sources/{id}/                 # Get details
  PATCH  /api/data-sources/{id}/                 # Update
  DELETE /api/data-sources/{id}/                 # Delete

Project Data Sources (project admin):
  GET    /api/projects/{pid}/data-sources/                 # List linked sources
  POST   /api/projects/{pid}/data-sources/                 # Link source
  DELETE /api/projects/{pid}/data-sources/{id}/            # Unlink
  POST   /api/projects/{pid}/data-sources/{id}/authorize/  # Start OAuth

User Credentials:
  GET    /api/data-sources/credentials/                    # List my credentials
  DELETE /api/data-sources/credentials/{id}/               # Revoke
  POST   /api/data-sources/credentials/{id}/reauthorize/   # Re-auth

Materialized Datasets:
  GET    /api/projects/{pid}/datasets/                     # List datasets
  POST   /api/projects/{pid}/datasets/{id}/sync/           # Trigger sync
  GET    /api/projects/{pid}/datasets/{id}/status/         # Sync status

OAuth Callbacks:
  GET    /api/oauth/callback/commcare/
  GET    /api/oauth/callback/commcare-connect/
```

---

## Part 7: Agent Integration

### Query Routing

When building the agent's database connection, include materialized schemas in the search path:

```python
def get_agent_search_path(project: Project, user: User) -> str:
    """Build PostgreSQL search_path for agent queries."""
    schemas = [project.db_schema]
    
    for pds in project.project_data_sources.filter(is_active=True):
        dataset = get_or_create_materialized_dataset(pds, user)
        
        if dataset.status == DatasetStatus.READY:
            schemas.append(dataset.schema_name)
        elif dataset.status in (DatasetStatus.PENDING, DatasetStatus.EXPIRED):
            # Trigger sync, agent proceeds without this data
            sync_dataset.delay(str(dataset.id))
    
    return ",".join(schemas)
```

### Activity Tracking

Update `last_activity_at` when the agent executes queries:

```python
# In apps/agents/tools/sql_tool.py
def execute_sql(query: str, project: Project, user: User):
    result = run_query(query)
    
    # Update activity for cleanup tracking
    MaterializedDataset.objects.filter(
        project_data_source__project=project,
        user=user,
        status=DatasetStatus.READY,
    ).update(last_activity_at=timezone.now())
    
    return result
```

### Data Dictionary Integration

After sync completes, update the project's data dictionary to include materialized tables:
- Include schema prefix in table names
- Add source indicator (e.g., "External: CommCare")
- Refresh automatically when sync completes

---

## Part 8: Frontend Integration

### New UI Components

**Project Settings - Data Sources:**
```
Data Sources
├── Connected Sources
│   ├── CommCare (project-level) - Ready, last sync 2h ago
│   │   └── [Sync Now] [Configure] [Remove]
│   └── CommCare Connect (user-level) - 3/5 users connected
│       └── [Configure] [Remove]
│
└── [+ Connect Data Source]
    └── Modal: Select type → Configure → Start OAuth
```

**User Profile - My Connections:**
```
My Data Connections
├── CommCare - Connected as john@example.com
│   └── [Disconnect]
└── CommCare Connect - Needs re-authorization
    └── [Reconnect]
```

**Chat - Status Indicators:**
```
When syncing:
┌─────────────────────────────────────────┐
│ Syncing CommCare data... 450/1200       │
└─────────────────────────────────────────┘

When credential expired:
┌─────────────────────────────────────────┐
│ CommCare connection expired [Reconnect] │
└─────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Database Credential Separation
1. Create `DatabaseConnection` model
2. Migrate existing credentials
3. Update Project model
4. Add API endpoints
5. Update frontend settings

### Phase 2: Data Source Foundation
1. Create models: `DataSource`, `ProjectDataSource`, `DataSourceCredential`
2. Create models: `MaterializedDataset`, `SyncJob`
3. Implement connector base class
4. Add API endpoints for configuration

### Phase 3: CommCare Connector
1. Implement `CommCareConnector`
2. OAuth flow integration
3. Form data sync (JSON storage like POC)
4. Schema creation and management

### Phase 4: Background Jobs
1. Set up Celery Beat
2. Implement sync task
3. Implement refresh/cleanup tasks
4. Token refresh automation

### Phase 5: Agent Integration
1. Dynamic search_path
2. Activity tracking
3. Data dictionary updates

### Phase 6: Frontend
1. Data source configuration UI
2. User credential management
3. Sync status in chat

### Phase 7: CommCare Connect Connector
1. Implement `CommCareConnectConnector`
2. Opportunities, visits, payments sync

---

## Design Decisions

1. **Incremental sync**: **Full refresh** - Drop and recreate tables each sync. Simpler implementation, guaranteed consistency. Acceptable given daily refresh cadence and 24h data retention.

2. **Schema versioning**: **Schema follows data** - Connector infers schema from API response each sync. Tables are recreated with whatever fields come back. No explicit schema definitions to maintain.

3. **Multi-tenant database**: **Same database** - Materialized schemas live alongside the project's main schema. Enables joins between materialized and existing data. Agent's search_path includes all relevant schemas.

4. **Rate limiting**: **Pause and resume** - Save sync progress, pause the job when rate limited, automatically resume after the rate limit window expires. Resilient to long rate limit windows without losing progress.
