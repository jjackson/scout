"""
Metadata service for the MCP server.

Provides functions to retrieve and format database metadata from the
project's cached data dictionary and TableKnowledge enrichments.
Regenerates the data dictionary if it's missing or stale.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Regenerate if older than this
STALE_THRESHOLD = timedelta(hours=24)


def _load_project(project_id: str) -> Any:
    """Load a Project instance from the database."""
    from apps.projects.models import Project

    return Project.objects.select_related("database_connection").get(id=project_id)


def _ensure_data_dictionary(project: Any) -> dict:
    """Return the project's data dictionary, regenerating if stale or missing."""
    dd = project.data_dictionary
    generated_at = project.data_dictionary_generated_at

    is_stale = (
        not dd
        or not generated_at
        or datetime.now(UTC) - generated_at > STALE_THRESHOLD
    )

    if is_stale:
        logger.info("Regenerating data dictionary for project '%s'", project.name)
        from apps.projects.services.data_dictionary import DataDictionaryGenerator

        generator = DataDictionaryGenerator(project)
        dd = generator.generate()

    return dd


def _get_table_knowledge(project_id: str, table_name: str) -> dict | None:
    """Fetch TableKnowledge enrichment for a specific table, if it exists."""
    from apps.knowledge.models import TableKnowledge

    tk = TableKnowledge.objects.filter(
        project_id=project_id,
        table_name=table_name,
    ).first()

    if not tk:
        return None

    result = {}
    if tk.description:
        result["description"] = tk.description
    if tk.use_cases:
        result["use_cases"] = tk.use_cases
    if tk.data_quality_notes:
        result["data_quality_notes"] = tk.data_quality_notes
    if tk.owner:
        result["owner"] = tk.owner
    if tk.refresh_frequency:
        result["refresh_frequency"] = tk.refresh_frequency
    if tk.related_tables:
        result["related_tables"] = tk.related_tables
    if tk.column_notes:
        result["column_notes"] = tk.column_notes
    return result


def _get_all_table_knowledge(project_id: str) -> dict[str, dict]:
    """Fetch all TableKnowledge entries for a project, keyed by table name."""
    from apps.knowledge.models import TableKnowledge

    result = {}
    for tk in TableKnowledge.objects.filter(project_id=project_id):
        entry = {}
        if tk.description:
            entry["description"] = tk.description
        if tk.use_cases:
            entry["use_cases"] = tk.use_cases
        if tk.data_quality_notes:
            entry["data_quality_notes"] = tk.data_quality_notes
        if tk.column_notes:
            entry["column_notes"] = tk.column_notes
        if entry:
            result[tk.table_name] = entry
    return result


def list_tables(project_id: str) -> list[dict]:
    """
    Return a list of tables in the project's schema.

    Each entry includes: name, type, row_count, description, column_count.
    Merges TableKnowledge descriptions where available.
    """
    project = _load_project(project_id)
    dd = _ensure_data_dictionary(project)
    tables = dd.get("tables", {})

    # Batch-load knowledge for all tables
    knowledge = _get_all_table_knowledge(project_id)

    result = []
    for table_name, table_info in tables.items():
        desc = table_info.get("comment", "")
        tk = knowledge.get(table_name)
        if tk and tk.get("description"):
            desc = tk["description"]

        result.append({
            "name": table_name,
            "type": "table",
            "row_count": table_info.get("row_count", 0),
            "column_count": len(table_info.get("columns", [])),
            "description": desc,
        })

    return result


def describe_table(project_id: str, table_name: str) -> dict | None:
    """
    Return detailed metadata for a single table.

    Returns None if the table is not found. Includes columns, primary keys,
    foreign keys, indexes, and TableKnowledge enrichments.
    """
    project = _load_project(project_id)
    dd = _ensure_data_dictionary(project)
    tables = dd.get("tables", {})

    # Case-insensitive lookup
    table_info = tables.get(table_name)
    if not table_info:
        table_lower = table_name.lower()
        for name, info in tables.items():
            if name.lower() == table_lower:
                table_name = name
                table_info = info
                break

    if not table_info:
        return None

    result = {
        "name": table_name,
        "row_count": table_info.get("row_count", 0),
        "comment": table_info.get("comment", ""),
        "columns": table_info.get("columns", []),
        "primary_key": table_info.get("primary_key", []),
        "foreign_keys": table_info.get("foreign_keys", []),
        "indexes": table_info.get("indexes", []),
    }

    # Merge TableKnowledge enrichments
    tk = _get_table_knowledge(project_id, table_name)
    if tk:
        result["knowledge"] = tk

    return result


def get_metadata(project_id: str) -> dict:
    """
    Return a complete metadata snapshot for the project's schema.

    Includes all tables with their columns and relationships,
    enum types, and TableKnowledge enrichments.
    """
    project = _load_project(project_id)
    dd = _ensure_data_dictionary(project)
    tables_raw = dd.get("tables", {})
    knowledge = _get_all_table_knowledge(project_id)

    tables = {}
    for table_name, table_info in tables_raw.items():
        entry = {
            "row_count": table_info.get("row_count", 0),
            "comment": table_info.get("comment", ""),
            "columns": table_info.get("columns", []),
            "primary_key": table_info.get("primary_key", []),
            "foreign_keys": table_info.get("foreign_keys", []),
            "indexes": table_info.get("indexes", []),
        }
        tk = knowledge.get(table_name)
        if tk:
            entry["knowledge"] = tk
        tables[table_name] = entry

    return {
        "schema": dd.get("schema", ""),
        "generated_at": dd.get("generated_at", ""),
        "table_count": len(tables),
        "tables": tables,
        "enums": dd.get("enums", {}),
    }


def suggest_tables(project_id: str, table_name: str) -> list[str]:
    """Return table name suggestions for a miss (case-insensitive + partial match)."""
    project = _load_project(project_id)
    dd = _ensure_data_dictionary(project)
    available = sorted(dd.get("tables", {}).keys())
    table_lower = table_name.lower()

    # Exact case-insensitive match
    exact = [t for t in available if t.lower() == table_lower]
    if exact:
        return exact

    # Partial match
    partial = [t for t in available if table_lower in t.lower()]
    if partial:
        return partial[:5]

    return available[:10]
