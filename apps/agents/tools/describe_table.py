"""
Describe table tool for the Scout data agent platform.

This module provides a factory function to create a tool that returns detailed
column information for a specific table from the project's data dictionary.
This tool is particularly useful for schemas with many tables (>15), where
including full column details in the system prompt would be prohibitively large.

The tool enables on-demand schema exploration, allowing the agent to look up
specific table structures as needed rather than having everything in context.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.tools import tool

if TYPE_CHECKING:
    from apps.projects.models import Project

logger = logging.getLogger(__name__)


def create_describe_table_tool(project: "Project"):
    """
    Create a tool for describing table structure from the data dictionary.

    The returned tool provides detailed column information including:
    - Column names and data types
    - Nullability and default values
    - Primary key indicators
    - Foreign key relationships
    - Column comments and sample values

    This tool is essential for large schemas where full details cannot fit
    in the system prompt. The agent should use this tool before writing
    queries against unfamiliar tables.

    Args:
        project: The Project model instance containing the data dictionary.

    Returns:
        A LangChain tool function that describes tables.

    Example:
        >>> tool = create_describe_table_tool(project)
        >>> result = tool.invoke({"table_name": "orders"})
    """

    @tool
    def describe_table(table_name: str) -> str:
        """
        Get detailed column information for a specific table.

        Use this tool before writing queries against tables you haven't
        examined recently. It provides:
        - All column names with their exact data types
        - Which columns are nullable vs required
        - Primary and foreign key relationships
        - Column descriptions and sample values

        This information helps you write correct queries on the first try,
        avoiding errors from misspelled column names or type mismatches.

        Args:
            table_name: The name of the table to describe. Must be a table
                that exists in the project's schema. Table names are
                case-sensitive.

        Returns:
            A formatted markdown string with complete table documentation,
            including columns, types, constraints, and relationships.
            Returns an error message if the table doesn't exist.

        Example:
            >>> describe_table("orders")
            ## orders
            Description: Customer orders and transactions
            Approximate rows: 1,234,567

            | Column | Type | Nullable | PK | Description |
            |--------|------|----------|----|-------------|
            | id | uuid | | * | Primary key |
            | user_id | uuid | | | Foreign key to users |
            | amount | numeric(10,2) | | | Order total in cents |
            ...

            Relationships:
            - user_id -> users.id
        """
        dd = project.data_dictionary

        # Handle missing data dictionary
        if not dd:
            logger.warning(
                "describe_table called but no data dictionary for project %s",
                project.slug,
            )
            return (
                "No data dictionary is available for this project. "
                "Please ask an administrator to generate the data dictionary "
                "using the `generate_data_dictionary` management command."
            )

        tables = dd.get("tables", {})

        # Handle table not found
        if table_name not in tables:
            available_tables = sorted(tables.keys())

            # Try case-insensitive match
            table_lower = table_name.lower()
            matches = [t for t in available_tables if t.lower() == table_lower]

            if matches:
                # Found a case-insensitive match
                return (
                    f"Table '{table_name}' not found. Did you mean '{matches[0]}'?\n\n"
                    f"Use: describe_table(\"{matches[0]}\")"
                )

            # Try partial matches for suggestions
            partial_matches = [t for t in available_tables if table_lower in t.lower()]

            suggestion = ""
            if partial_matches:
                suggestion = f"\n\nDid you mean one of these?\n- " + "\n- ".join(partial_matches[:5])

            if len(available_tables) <= 20:
                return (
                    f"Table '{table_name}' not found in the data dictionary.\n\n"
                    f"Available tables:\n- " + "\n- ".join(available_tables) +
                    suggestion
                )
            else:
                return (
                    f"Table '{table_name}' not found in the data dictionary.\n\n"
                    f"There are {len(available_tables)} tables available. "
                    f"First 20: {', '.join(available_tables[:20])}..." +
                    suggestion
                )

        # Build the table description
        tinfo = tables[table_name]
        lines: list[str] = []

        # Header
        lines.append(f"## {table_name}")
        lines.append("")

        # Description/comment
        if tinfo.get("comment"):
            lines.append(f"**Description:** {tinfo['comment']}")
            lines.append("")

        # Row count
        row_count = tinfo.get("row_count", 0)
        if row_count:
            lines.append(f"**Approximate rows:** {row_count:,}")
        else:
            lines.append("**Approximate rows:** Unknown")
        lines.append("")

        # Column table
        columns = tinfo.get("columns", [])
        if columns:
            lines.append("### Columns")
            lines.append("")
            lines.append("| Column | Type | Nullable | PK | Description | Sample Values |")
            lines.append("|--------|------|----------|----:|-------------|---------------|")

            for col in columns:
                name = col.get("name", "")
                col_type = col.get("type", "unknown")
                nullable = "Yes" if col.get("nullable") else ""
                pk = "*" if col.get("is_primary_key") else ""
                comment = col.get("comment", "") or ""
                samples = col.get("sample_values")

                # Format sample values
                if samples:
                    # Truncate long sample values
                    sample_strs = []
                    for s in samples[:3]:
                        s_str = str(s) if s is not None else "NULL"
                        if len(s_str) > 20:
                            s_str = s_str[:17] + "..."
                        sample_strs.append(f"`{s_str}`")
                    sample_str = ", ".join(sample_strs)
                else:
                    sample_str = ""

                # Truncate long comments
                if len(comment) > 40:
                    comment = comment[:37] + "..."

                lines.append(f"| {name} | {col_type} | {nullable} | {pk} | {comment} | {sample_str} |")

            lines.append("")

        # Default values (if any columns have them)
        defaults = [(col["name"], col["default"]) for col in columns if col.get("default")]
        if defaults:
            lines.append("### Default Values")
            lines.append("")
            for col_name, default_val in defaults:
                # Clean up default value display
                if default_val and len(str(default_val)) > 50:
                    default_val = str(default_val)[:47] + "..."
                lines.append(f"- `{col_name}`: {default_val}")
            lines.append("")

        # Foreign keys
        fks = tinfo.get("foreign_keys", [])
        if fks:
            lines.append("### Relationships (Foreign Keys)")
            lines.append("")
            for fk in fks:
                col = fk.get("column", "")
                ref_table = fk.get("references_table", "")
                ref_col = fk.get("references_column", "")
                lines.append(f"- `{col}` -> `{ref_table}.{ref_col}`")
            lines.append("")

        # Indexes (excluding primary key)
        indexes = tinfo.get("indexes", [])
        if indexes:
            lines.append("### Indexes")
            lines.append("")
            for idx in indexes:
                idx_name = idx.get("name", "")
                idx_cols = idx.get("columns", [])
                is_unique = idx.get("unique", False)
                unique_str = " (unique)" if is_unique else ""
                cols_str = ", ".join(f"`{c}`" for c in idx_cols)
                lines.append(f"- **{idx_name}**: {cols_str}{unique_str}")
            lines.append("")

        # Check for table knowledge (enriched metadata)
        try:
            from apps.knowledge.models import TableKnowledge

            tk = TableKnowledge.objects.filter(
                project=project,
                table_name=table_name,
            ).first()

            if tk:
                lines.append("### Additional Context")
                lines.append("")

                if tk.description and tk.description != tinfo.get("comment", ""):
                    lines.append(f"**Business Description:** {tk.description}")
                    lines.append("")

                if tk.use_cases:
                    lines.append("**Use Cases:**")
                    for use_case in tk.use_cases:
                        lines.append(f"- {use_case}")
                    lines.append("")

                if tk.data_quality_notes:
                    lines.append("**Data Quality Notes:**")
                    for note in tk.data_quality_notes:
                        lines.append(f"- {note}")
                    lines.append("")

                if tk.column_notes:
                    lines.append("**Column-Specific Notes:**")
                    for col_name, note in tk.column_notes.items():
                        lines.append(f"- `{col_name}`: {note}")
                    lines.append("")

                if tk.refresh_frequency:
                    lines.append(f"**Data Freshness:** {tk.refresh_frequency}")
                    lines.append("")

                if tk.related_tables:
                    lines.append("**Commonly Joined With:**")
                    for relation in tk.related_tables:
                        if isinstance(relation, dict):
                            rel_table = relation.get("table", "")
                            join_hint = relation.get("join_hint", "")
                            note = relation.get("note", "")
                            if join_hint:
                                lines.append(f"- `{rel_table}`: `{join_hint}`")
                                if note:
                                    lines.append(f"  - {note}")
                            else:
                                lines.append(f"- `{rel_table}`")
                        else:
                            lines.append(f"- `{relation}`")
                    lines.append("")

        except Exception as e:
            # Don't fail if table knowledge lookup fails
            logger.debug("Could not fetch TableKnowledge for %s: %s", table_name, e)

        return "\n".join(lines).rstrip()

    # Set the tool name explicitly
    describe_table.name = "describe_table"

    return describe_table


__all__ = [
    "create_describe_table_tool",
]
