"""
Knowledge Retriever service for Scout data agent platform.

Assembles knowledge context from multiple sources into a formatted markdown
string suitable for inclusion in the agent's system prompt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.knowledge.models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    TableKnowledge,
    VerifiedQuery,
)

if TYPE_CHECKING:
    from apps.projects.models import Project


class KnowledgeRetriever:
    """
    Retrieves and formats knowledge context for an agent's system prompt.

    This class aggregates knowledge from multiple sources:
    - Canonical metrics (source of truth for metric definitions)
    - Business rules (institutional knowledge and gotchas)
    - Table knowledge (enriched metadata beyond the data dictionary)
    - Verified queries (patterns known to produce correct results)
    - Agent learnings (corrections discovered through trial and error)

    The formatted output is designed to be injected into the agent's system
    prompt to provide context that helps generate accurate SQL queries.
    """

    # Configuration constants
    MAX_VERIFIED_QUERIES = 10
    MAX_AGENT_LEARNINGS = 20

    def __init__(self, project: Project) -> None:
        """
        Initialize the retriever for a specific project.

        Args:
            project: The project to retrieve knowledge for.
        """
        self.project = project

    def retrieve(self, user_question: str = "") -> str:
        """
        Retrieve and format all relevant knowledge as markdown.

        Assembles knowledge from all sources into a formatted string suitable
        for inclusion in the agent's system prompt. The user_question parameter
        is reserved for future semantic filtering but currently unused.

        Args:
            user_question: The user's question (reserved for future use).

        Returns:
            Formatted markdown string containing all relevant knowledge.
        """
        sections: list[str] = []

        # Always include canonical metrics - they're the source of truth
        metrics_section = self._format_canonical_metrics()
        if metrics_section:
            sections.append(metrics_section)

        # Always include business rules - they prevent expensive mistakes
        rules_section = self._format_business_rules()
        if rules_section:
            sections.append(rules_section)

        # Include table knowledge for enriched context
        tables_section = self._format_table_knowledge()
        if tables_section:
            sections.append(tables_section)

        # Include verified query patterns
        queries_section = self._format_verified_queries()
        if queries_section:
            sections.append(queries_section)

        # Include active agent learnings
        learnings_section = self._format_agent_learnings()
        if learnings_section:
            sections.append(learnings_section)

        return "\n\n".join(sections)

    def _format_canonical_metrics(self) -> str:
        """
        Format canonical metrics as markdown with SQL code blocks.

        Returns:
            Formatted markdown section or empty string if no metrics exist.
        """
        metrics = CanonicalMetric.objects.filter(project=self.project).order_by("name")

        if not metrics.exists():
            return ""

        lines: list[str] = ["## Canonical Metric Definitions", ""]

        for metric in metrics:
            lines.append(f"### {metric.name}")
            lines.append("")
            lines.append(f"**Definition:** {metric.definition}")
            lines.append("")

            if metric.unit:
                lines.append(f"**Unit:** {metric.unit}")
                lines.append("")

            lines.append("**SQL:**")
            lines.append("```sql")
            lines.append(metric.sql_template.strip())
            lines.append("```")
            lines.append("")

            if metric.caveats:
                lines.append("**Caveats:**")
                for caveat in metric.caveats:
                    lines.append(f"- {caveat}")
                lines.append("")

        return "\n".join(lines).rstrip()

    def _format_business_rules(self) -> str:
        """
        Format business rules as a markdown bullet list.

        Returns:
            Formatted markdown section or empty string if no rules exist.
        """
        rules = BusinessRule.objects.filter(project=self.project).order_by("title")

        if not rules.exists():
            return ""

        lines: list[str] = ["## Business Rules & Gotchas", ""]

        for rule in rules:
            lines.append(f"- **{rule.title}:** {rule.description}")

            # Add context about which tables/metrics this applies to
            context_parts: list[str] = []
            if rule.applies_to_tables:
                tables_str = ", ".join(rule.applies_to_tables)
                context_parts.append(f"Tables: {tables_str}")
            if rule.applies_to_metrics:
                metrics_str = ", ".join(rule.applies_to_metrics)
                context_parts.append(f"Metrics: {metrics_str}")

            if context_parts:
                lines.append(f"  - *Applies to: {'; '.join(context_parts)}*")

        return "\n".join(lines)

    def _format_table_knowledge(self) -> str:
        """
        Format table knowledge with column notes and data quality notes.

        Returns:
            Formatted markdown section or empty string if no table knowledge exists.
        """
        tables = TableKnowledge.objects.filter(project=self.project).order_by(
            "table_name"
        )

        if not tables.exists():
            return ""

        lines: list[str] = ["## Table Context (beyond schema)", ""]

        for table in tables:
            lines.append(f"### {table.table_name}")
            lines.append("")
            lines.append(table.description)
            lines.append("")

            # Column-level notes
            if table.column_notes:
                lines.append("**Column Notes:**")
                for column, note in table.column_notes.items():
                    lines.append(f"- `{column}`: {note}")
                lines.append("")

            # Data quality notes
            if table.data_quality_notes:
                lines.append("**Data Quality Notes:**")
                for note in table.data_quality_notes:
                    lines.append(f"- {note}")
                lines.append("")

            # Related tables with join hints
            if table.related_tables:
                lines.append("**Related Tables:**")
                for relation in table.related_tables:
                    if isinstance(relation, dict):
                        related_table = relation.get("table", "")
                        join_hint = relation.get("join_hint", "")
                        if join_hint:
                            lines.append(f"- `{related_table}`: `{join_hint}`")
                        else:
                            lines.append(f"- `{related_table}`")
                    else:
                        # Handle simple string format
                        lines.append(f"- `{relation}`")
                lines.append("")

            # Refresh frequency if specified
            if table.refresh_frequency:
                lines.append(f"**Refresh Frequency:** {table.refresh_frequency}")
                lines.append("")

        return "\n".join(lines).rstrip()

    def _format_verified_queries(self) -> str:
        """
        Format verified query patterns with SQL code blocks.

        Includes the top queries by verified date (most recently verified first),
        limited to MAX_VERIFIED_QUERIES.

        Returns:
            Formatted markdown section or empty string if no queries exist.
        """
        queries = VerifiedQuery.objects.filter(project=self.project).order_by("name")[
            : self.MAX_VERIFIED_QUERIES
        ]

        if not queries.exists():
            return ""

        lines: list[str] = ["## Verified Query Patterns", ""]

        for query in queries:
            lines.append(f"### {query.name}")
            lines.append("")
            lines.append(f"**Question:** {query.description}")
            lines.append("")

            if query.tables_used:
                tables_str = ", ".join(f"`{t}`" for t in query.tables_used)
                lines.append(f"**Tables:** {tables_str}")
                lines.append("")

            lines.append("**SQL:**")
            lines.append("```sql")
            lines.append(query.sql.strip())
            lines.append("```")
            lines.append("")

        return "\n".join(lines).rstrip()

    def _format_agent_learnings(self) -> str:
        """
        Format active agent learnings as a bullet list.

        Includes active learnings ordered by confidence_score (descending),
        limited to MAX_AGENT_LEARNINGS.

        Returns:
            Formatted markdown section or empty string if no learnings exist.
        """
        learnings = AgentLearning.objects.filter(
            project=self.project,
            is_active=True,
        ).order_by("-confidence_score", "-times_applied")[: self.MAX_AGENT_LEARNINGS]

        if not learnings.exists():
            return ""

        lines: list[str] = ["## Learned Corrections", ""]

        for learning in learnings:
            # Format the main learning description
            lines.append(f"- {learning.description}")

            # Add context about which tables this applies to
            if learning.applies_to_tables:
                tables_str = ", ".join(f"`{t}`" for t in learning.applies_to_tables)
                lines.append(f"  - *Tables: {tables_str}*")

            # Include confidence indicator for high-confidence learnings
            if learning.confidence_score >= 0.8:
                lines.append(
                    f"  - *Confidence: {learning.confidence_score:.0%} "
                    f"(applied {learning.times_applied} times)*"
                )

        return "\n".join(lines)
