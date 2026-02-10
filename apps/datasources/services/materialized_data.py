"""
Service for managing materialized data access for agents.

This module provides functions to:
- Get or create materialized datasets for a user
- Track activity on materialized data (for cleanup scheduling)
- Build search_path including materialized schemas
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

if TYPE_CHECKING:
    from apps.datasources.models import MaterializedDataset
    from apps.projects.models import Project
    from apps.users.models import User

logger = logging.getLogger(__name__)


def get_user_materialized_schemas(project: Project, user: User) -> list[str]:
    """
    Get all active materialized schema names for a user in a project.

    This returns schemas from:
    1. Project-level data sources (shared credentials)
    2. User-level data sources (user's own OAuth credentials)

    Args:
        project: The project to get schemas for
        user: The user requesting access

    Returns:
        List of PostgreSQL schema names that contain materialized data
    """
    from apps.datasources.models import CredentialMode, DatasetStatus, MaterializedDataset

    schemas = []

    # Get project-level materialized datasets (shared by all users)
    project_datasets = MaterializedDataset.objects.filter(
        project_data_source__project=project,
        project_data_source__credential_mode=CredentialMode.PROJECT,
        status__in=[DatasetStatus.READY, DatasetStatus.SYNCING],
        user__isnull=True,
    ).values_list("schema_name", flat=True)

    schemas.extend(project_datasets)

    # Get user-level materialized datasets (user's own data)
    user_datasets = MaterializedDataset.objects.filter(
        project_data_source__project=project,
        project_data_source__credential_mode=CredentialMode.USER,
        status__in=[DatasetStatus.READY, DatasetStatus.SYNCING],
        user=user,
    ).values_list("schema_name", flat=True)

    schemas.extend(user_datasets)

    return list(schemas)


def build_search_path(project: Project, user: User | None = None) -> str:
    """
    Build a PostgreSQL search_path that includes materialized data schemas.

    The search_path order is:
    1. Project's main schema (for direct database queries)
    2. Project-level materialized schemas (shared data)
    3. User-level materialized schemas (user's own data)

    Args:
        project: The project to build search_path for
        user: Optional user for user-level schemas

    Returns:
        A PostgreSQL search_path string (e.g., "public, commcare_proj1, user_123_commcare")
    """
    schemas = [project.db_schema]  # Start with project's main schema

    if user:
        materialized_schemas = get_user_materialized_schemas(project, user)
        schemas.extend(materialized_schemas)

    # Deduplicate while preserving order
    seen = set()
    unique_schemas = []
    for schema in schemas:
        if schema not in seen:
            seen.add(schema)
            unique_schemas.append(schema)

    return ", ".join(unique_schemas)


def track_materialized_data_activity(project: Project, user: User) -> None:
    """
    Update last_activity_at for all materialized datasets a user has access to.

    This is called when the user executes a query to track activity
    for the cleanup scheduler.

    Args:
        project: The project being queried
        user: The user executing the query
    """
    from apps.datasources.models import CredentialMode, DatasetStatus, MaterializedDataset

    now = timezone.now()

    # Update project-level datasets
    MaterializedDataset.objects.filter(
        project_data_source__project=project,
        project_data_source__credential_mode=CredentialMode.PROJECT,
        status__in=[DatasetStatus.READY, DatasetStatus.SYNCING],
        user__isnull=True,
    ).update(last_activity_at=now)

    # Update user-level datasets
    MaterializedDataset.objects.filter(
        project_data_source__project=project,
        project_data_source__credential_mode=CredentialMode.USER,
        status__in=[DatasetStatus.READY, DatasetStatus.SYNCING],
        user=user,
    ).update(last_activity_at=now)

    logger.debug(
        "Updated activity timestamp for materialized datasets: project=%s, user=%s",
        project.slug,
        user.id,
    )


def get_or_create_user_dataset(
    project: Project,
    user: User,
    data_source_type: str,
) -> MaterializedDataset | None:
    """
    Get or create a materialized dataset for a user-level data source.

    If the user doesn't have credentials for the data source, returns None.

    Args:
        project: The project
        user: The user
        data_source_type: The type of data source (e.g., "commcare")

    Returns:
        MaterializedDataset instance or None if no credentials
    """
    from apps.datasources.models import (
        CredentialMode,
        DatasetStatus,
        DataSourceCredential,
        MaterializedDataset,
        ProjectDataSource,
    )

    # Find project data source with user-level credentials
    try:
        project_data_source = ProjectDataSource.objects.get(
            project=project,
            data_source__source_type=data_source_type,
            credential_mode=CredentialMode.USER,
            is_active=True,
        )
    except ProjectDataSource.DoesNotExist:
        logger.debug(
            "No user-level %s data source configured for project %s",
            data_source_type,
            project.slug,
        )
        return None

    # Check if user has valid credentials
    has_credentials = DataSourceCredential.objects.filter(
        data_source=project_data_source.data_source,
        user=user,
        is_valid=True,
    ).exists()

    if not has_credentials:
        logger.debug(
            "User %s has no valid credentials for %s in project %s",
            user.id,
            data_source_type,
            project.slug,
        )
        return None

    # Get or create the materialized dataset
    with transaction.atomic():
        dataset, created = MaterializedDataset.objects.get_or_create(
            project_data_source=project_data_source,
            user=user,
            defaults={
                "schema_name": f"user_{user.id}_{data_source_type}",
                "status": DatasetStatus.PENDING,
            },
        )

        if created:
            logger.info(
                "Created materialized dataset for user %s, %s in project %s",
                user.id,
                data_source_type,
                project.slug,
            )

    return dataset


def ensure_user_datasets_exist(project: Project, user: User) -> list[MaterializedDataset]:
    """
    Ensure materialized datasets exist for all user-level data sources.

    This is called when a user starts a chat session to ensure their
    data is being synced.

    Args:
        project: The project
        user: The user

    Returns:
        List of MaterializedDataset instances
    """
    from apps.datasources.models import CredentialMode, DataSourceType, ProjectDataSource

    datasets = []

    # Get all user-level data sources for this project
    project_data_sources = ProjectDataSource.objects.filter(
        project=project,
        credential_mode=CredentialMode.USER,
        is_active=True,
    ).select_related("data_source")

    for pds in project_data_sources:
        dataset = get_or_create_user_dataset(
            project=project,
            user=user,
            data_source_type=pds.data_source.source_type,
        )
        if dataset:
            datasets.append(dataset)

    return datasets


__all__ = [
    "get_user_materialized_schemas",
    "build_search_path",
    "track_materialized_data_activity",
    "get_or_create_user_dataset",
    "ensure_user_datasets_exist",
]
