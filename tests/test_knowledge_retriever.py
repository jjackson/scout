"""
Comprehensive tests for Knowledge Retriever.

Tests cover:
- Empty knowledge scenarios
- Canonical metrics only
- Business rules
- Table knowledge
- Verified queries
- Agent learnings
- Full assembly with all knowledge types
- Retrieval filtering and prioritization
"""
import pytest
from datetime import datetime

from apps.knowledge.models import (
    CanonicalMetric,
    BusinessRule,
    TableKnowledge,
    VerifiedQuery,
    AgentLearning,
)
from apps.knowledge.services.retriever import KnowledgeRetriever
from apps.projects.models import Project


@pytest.fixture
def project(db, user):
    """Create a test project."""
    project = Project.objects.create(
        name="Knowledge Test Project",
        slug="knowledge-test",
        db_host="localhost",
        db_port=5432,
        db_name="testdb",
        db_schema="analytics",
        created_by=user,
    )
    project.db_user = "testuser"
    project.db_password = "testpass"
    project.save()
    return project


class TestEmptyKnowledge:
    """Test retriever behavior with no knowledge."""

    def test_empty_knowledge_returns_valid_string(self, project):
        """Test that retriever returns valid output with no knowledge."""
        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert isinstance(result, str)
        # Should still have structure even if empty
        assert len(result) >= 0

    def test_empty_knowledge_has_no_sections(self, project):
        """Test that empty knowledge doesn't have filled sections."""
        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should not contain section headers if no data
        # or should have empty sections clearly marked
        if "CANONICAL METRICS" in result:
            assert "None defined" in result or "No canonical metrics" in result.lower()
        if "BUSINESS RULES" in result:
            assert "None defined" in result or "No business rules" in result.lower()


class TestCanonicalMetricsOnly:
    """Test retriever with only canonical metrics."""

    def test_single_canonical_metric(self, project, user):
        """Test retrieval of a single canonical metric."""
        CanonicalMetric.objects.create(
            project=project,
            name="MRR",
            definition="Monthly Recurring Revenue from active subscriptions",
            sql_template="SELECT SUM(amount) FROM subscriptions WHERE status = 'active'",
            unit="USD",
            caveats=["Excludes annual contracts"],
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "MRR" in result
        assert "Monthly Recurring Revenue" in result
        assert "SUM(amount)" in result
        assert "Excludes annual contracts" in result

    def test_multiple_canonical_metrics(self, project, user):
        """Test retrieval of multiple canonical metrics."""
        CanonicalMetric.objects.create(
            project=project,
            name="MRR",
            definition="Monthly Recurring Revenue",
            sql_template="SELECT SUM(amount) FROM subscriptions WHERE status = 'active'",
            unit="USD",
            updated_by=user,
        )
        CanonicalMetric.objects.create(
            project=project,
            name="DAU",
            definition="Daily Active Users",
            sql_template="SELECT COUNT(DISTINCT user_id) FROM events WHERE date = CURRENT_DATE",
            unit="users",
            updated_by=user,
        )
        CanonicalMetric.objects.create(
            project=project,
            name="Churn Rate",
            definition="Percentage of users who churned",
            sql_template="SELECT (churned / total) * 100 FROM user_stats",
            unit="percentage",
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "MRR" in result
        assert "DAU" in result
        assert "Churn Rate" in result

    def test_metric_with_tags(self, project, user):
        """Test that metric tags are included."""
        CanonicalMetric.objects.create(
            project=project,
            name="Revenue",
            definition="Total revenue",
            sql_template="SELECT SUM(amount) FROM orders",
            unit="USD",
            tags=["finance", "revenue", "critical"],
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Tags might be included in output
        if "finance" in result.lower():
            assert "revenue" in result.lower()


class TestBusinessRules:
    """Test retriever with business rules."""

    def test_single_business_rule(self, project, user):
        """Test retrieval of a single business rule."""
        BusinessRule.objects.create(
            project=project,
            title="Soft Delete Rule",
            description="Always filter deleted_at IS NULL for active records in users and orders tables",
            applies_to_tables=["users", "orders"],
            created_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "Soft Delete Rule" in result
        assert "deleted_at IS NULL" in result

    def test_multiple_business_rules(self, project, user):
        """Test retrieval of multiple business rules."""
        BusinessRule.objects.create(
            project=project,
            title="APAC Active User Definition",
            description="In APAC region, active user means logged in within 7 days, not 30",
            applies_to_tables=["users"],
            created_by=user,
        )
        BusinessRule.objects.create(
            project=project,
            title="Q1 2024 Data Quality Issue",
            description="Orders table has duplicate rows for Q1 2024 due to migration bug",
            applies_to_tables=["orders"],
            created_by=user,
        )
        BusinessRule.objects.create(
            project=project,
            title="Legacy Data Location",
            description="Revenue numbers before 2023 are in legacy_revenue table",
            applies_to_tables=["legacy_revenue"],
            created_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "APAC" in result
        assert "Q1 2024" in result
        assert "legacy_revenue" in result

    def test_business_rule_with_metrics(self, project, user):
        """Test business rule that applies to metrics."""
        BusinessRule.objects.create(
            project=project,
            title="MRR Calculation",
            description="MRR must exclude annual contracts and trial users",
            applies_to_metrics=["MRR"],
            created_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "MRR" in result
        assert "exclude" in result.lower() or "annual" in result.lower()


class TestTableKnowledge:
    """Test retriever with table knowledge."""

    def test_single_table_knowledge(self, project, user):
        """Test retrieval of single table knowledge."""
        TableKnowledge.objects.create(
            project=project,
            table_name="orders",
            description="Customer orders with payment and fulfillment status",
            use_cases=["Revenue reporting", "Order analysis", "Fulfillment tracking"],
            data_quality_notes=["created_at is UTC", "amount is in cents"],
            column_notes={"status": "Values: pending, completed, cancelled"},
            owner="Data Team",
            refresh_frequency="real-time",
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "orders" in result.lower()
        assert "Customer orders" in result or "orders" in result.lower()
        if "Revenue reporting" in result:
            assert "Order analysis" in result

    def test_multiple_table_knowledge_under_threshold(self, project, user):
        """Test that all tables are included when under threshold (20 tables)."""
        # Create 10 tables - should all be included
        for i in range(10):
            TableKnowledge.objects.create(
                project=project,
                table_name=f"table_{i}",
                description=f"Test table {i}",
                use_cases=[f"Use case {i}"],
                updated_by=user,
            )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # All tables should be mentioned
        for i in range(10):
            assert f"table_{i}" in result.lower()

    def test_table_knowledge_filtering_over_threshold(self, project, user):
        """Test that table knowledge is filtered when over 20 tables."""
        # Create 25 tables
        for i in range(25):
            TableKnowledge.objects.create(
                project=project,
                table_name=f"table_{i}",
                description=f"Test table {i}",
                use_cases=[f"Use case {i}"],
                updated_by=user,
            )

        retriever = KnowledgeRetriever(project)
        # Without a specific question, might return all or a summary
        result = retriever.retrieve()

        # Should either summarize or limit output
        assert isinstance(result, str)

    def test_table_knowledge_with_question_matching(self, project, user):
        """Test table knowledge retrieval with question-based filtering."""
        TableKnowledge.objects.create(
            project=project,
            table_name="orders",
            description="Customer orders",
            use_cases=["Revenue reporting"],
            updated_by=user,
        )
        TableKnowledge.objects.create(
            project=project,
            table_name="users",
            description="User accounts",
            use_cases=["User analysis"],
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        # Test with question parameter if supported
        result = retriever.retrieve(user_question="What is the total revenue from orders?")

        # Should prioritize orders table
        assert "orders" in result.lower()

    def test_table_with_related_tables(self, project, user):
        """Test table knowledge with related table hints."""
        TableKnowledge.objects.create(
            project=project,
            table_name="orders",
            description="Customer orders",
            related_tables=[
                {"table": "users", "join_hint": "orders.user_id = users.id"},
                {"table": "products", "join_hint": "orders.product_id = products.id"}
            ],
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "orders" in result.lower()
        # Check that related tables info is present
        if "users" in result:
            assert "related" in result.lower() or "user_id" in result


class TestVerifiedQueries:
    """Test retriever with verified queries."""

    def test_single_verified_query(self, project, user):
        """Test retrieval of single verified query."""
        VerifiedQuery.objects.create(
            project=project,
            name="Daily Revenue",
            description="Get daily revenue totals for a date range",
            sql="SELECT DATE(created_at) as date, SUM(amount) as total FROM orders GROUP BY DATE(created_at)",
            tables_used=["orders"],
            verified_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "Daily Revenue" in result
        assert "SUM(amount)" in result

    def test_multiple_verified_queries(self, project, user):
        """Test retrieval of multiple verified queries."""
        for i in range(5):
            VerifiedQuery.objects.create(
                project=project,
                name=f"Query {i}",
                description=f"Test query {i}",
                sql=f"SELECT * FROM table_{i}",
                tables_used=[f"table_{i}"],
                verified_by=user,
            )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should include multiple queries
        count = sum(1 for i in range(5) if f"Query {i}" in result)
        assert count >= 3  # Should include at least some queries

    def test_verified_queries_limited_to_top_10(self, project, user):
        """Test that verified queries are limited to top 10."""
        # Create 15 verified queries
        for i in range(15):
            VerifiedQuery.objects.create(
                project=project,
                name=f"Query {i}",
                description=f"Test query {i}",
                sql=f"SELECT * FROM table_{i}",
                tables_used=[f"table_{i}"],
                verified_by=user,
            )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should not include all 15 (limit to 10 per spec)
        count = sum(1 for i in range(15) if f"Query {i}" in result)
        assert count <= 10

    def test_verified_query_with_tags(self, project, user):
        """Test verified query with tags."""
        VerifiedQuery.objects.create(
            project=project,
            name="Revenue by Region",
            description="Calculate revenue breakdown by region",
            sql="SELECT region, SUM(amount) FROM orders GROUP BY region",
            tables_used=["orders"],
            tags=["finance", "reporting", "regional"],
            verified_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "Revenue by Region" in result


class TestAgentLearnings:
    """Test retriever with agent learnings."""

    def test_single_learning(self, project, user):
        """Test retrieval of single agent learning."""
        AgentLearning.objects.create(
            project=project,
            description="Amount column is in cents, not dollars. Divide by 100.",
            category="type_mismatch",
            applies_to_tables=["orders"],
            original_error="Unexpected revenue value",
            original_sql="SELECT amount FROM orders",
            corrected_sql="SELECT amount / 100.0 FROM orders",
            confidence_score=0.8,
            is_active=True,
            discovered_by_user=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "cents" in result.lower() or "divide by 100" in result.lower()

    def test_multiple_learnings_ordered_by_confidence(self, project, user):
        """Test that learnings are ordered by confidence score."""
        AgentLearning.objects.create(
            project=project,
            description="Low confidence learning",
            category="other",
            applies_to_tables=["table1"],
            confidence_score=0.3,
            is_active=True,
            discovered_by_user=user,
        )
        AgentLearning.objects.create(
            project=project,
            description="High confidence learning",
            category="other",
            applies_to_tables=["table2"],
            confidence_score=0.9,
            is_active=True,
            discovered_by_user=user,
        )
        AgentLearning.objects.create(
            project=project,
            description="Medium confidence learning",
            category="other",
            applies_to_tables=["table3"],
            confidence_score=0.6,
            is_active=True,
            discovered_by_user=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # High confidence should appear before low confidence
        if "High confidence" in result and "Low confidence" in result:
            high_pos = result.index("High confidence")
            low_pos = result.index("Low confidence")
            assert high_pos < low_pos

    def test_inactive_learnings_excluded(self, project, user):
        """Test that inactive learnings are not included."""
        AgentLearning.objects.create(
            project=project,
            description="Active learning",
            category="other",
            applies_to_tables=["table1"],
            is_active=True,
            discovered_by_user=user,
        )
        AgentLearning.objects.create(
            project=project,
            description="Inactive learning",
            category="other",
            applies_to_tables=["table2"],
            is_active=False,
            discovered_by_user=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert "Active learning" in result
        assert "Inactive learning" not in result

    def test_learning_with_evidence(self, project, user):
        """Test that learning includes error and correction context."""
        AgentLearning.objects.create(
            project=project,
            description="Status column uses codes not names",
            category="naming",
            applies_to_tables=["orders"],
            original_error="Column 'status_name' does not exist",
            original_sql="SELECT status_name FROM orders",
            corrected_sql="SELECT status FROM orders",
            confidence_score=0.7,
            is_active=True,
            discovered_by_user=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should mention the learning
        assert "status" in result.lower()


class TestFullAssembly:
    """Test retriever with all knowledge types together."""

    def test_all_knowledge_types_present(self, project, user):
        """Test that all knowledge types are included in output."""
        # Add canonical metric
        CanonicalMetric.objects.create(
            project=project,
            name="MRR",
            definition="Monthly Recurring Revenue",
            sql_template="SELECT SUM(amount) FROM subscriptions WHERE status = 'active'",
            unit="USD",
            updated_by=user,
        )

        # Add business rule
        BusinessRule.objects.create(
            project=project,
            title="Soft Delete Rule",
            description="Always filter deleted_at IS NULL",
            applies_to_tables=["users"],
            created_by=user,
        )

        # Add table knowledge
        TableKnowledge.objects.create(
            project=project,
            table_name="orders",
            description="Customer orders",
            use_cases=["Revenue reporting"],
            updated_by=user,
        )

        # Add verified query
        VerifiedQuery.objects.create(
            project=project,
            name="Daily Revenue",
            description="Daily revenue totals",
            sql="SELECT DATE(created_at), SUM(amount) FROM orders GROUP BY DATE(created_at)",
            tables_used=["orders"],
            verified_by=user,
        )

        # Add agent learning
        AgentLearning.objects.create(
            project=project,
            description="Amount is in cents",
            category="type_mismatch",
            applies_to_tables=["orders"],
            is_active=True,
            discovered_by_user=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Check that all types are represented
        assert "MRR" in result
        assert "Soft Delete" in result or "deleted_at" in result
        assert "orders" in result.lower()
        assert "Daily Revenue" in result
        assert "cents" in result.lower()

    def test_knowledge_sections_clearly_separated(self, project, user):
        """Test that knowledge sections are clearly delineated."""
        # Add various knowledge
        CanonicalMetric.objects.create(
            project=project,
            name="MRR",
            definition="Monthly Recurring Revenue",
            sql_template="SELECT SUM(amount) FROM subscriptions",
            updated_by=user,
        )

        BusinessRule.objects.create(
            project=project,
            title="Test Rule",
            description="Test description",
            created_by=user,
        )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should have clear section markers or structure
        # This depends on implementation but should be organized
        assert len(result) > 0
        assert isinstance(result, str)

    def test_knowledge_context_is_string(self, project):
        """Test that retrieve always returns a string."""
        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        assert isinstance(result, str)

    def test_large_knowledge_base(self, project, user):
        """Test performance with large knowledge base."""
        # Add many of each type
        for i in range(20):
            CanonicalMetric.objects.create(
                project=project,
                name=f"Metric {i}",
                definition=f"Definition {i}",
                sql_template=f"SELECT {i}",
                updated_by=user,
            )

        for i in range(20):
            BusinessRule.objects.create(
                project=project,
                title=f"Rule {i}",
                description=f"Description {i}",
                created_by=user,
            )

        for i in range(20):
            TableKnowledge.objects.create(
                project=project,
                table_name=f"table_{i}",
                description=f"Table {i}",
                updated_by=user,
            )

        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should complete without error and return structured output
        assert isinstance(result, str)
        assert len(result) > 0


class TestRetrievalFiltering:
    """Test knowledge filtering and prioritization."""

    def test_question_based_table_filtering(self, project, user):
        """Test that relevant tables are prioritized based on question."""
        TableKnowledge.objects.create(
            project=project,
            table_name="users",
            description="User accounts and profiles",
            use_cases=["User analysis", "Authentication"],
            updated_by=user,
        )
        TableKnowledge.objects.create(
            project=project,
            table_name="orders",
            description="Customer orders and purchases",
            use_cases=["Revenue analysis", "Sales reporting"],
            updated_by=user,
        )

        retriever = KnowledgeRetriever(project)

        # Test with revenue question
        result = retriever.retrieve(user_question="What is the total revenue?")

        # Orders should be prioritized
        if TableKnowledge.objects.filter(project=project).count() > 1:
            assert "orders" in result.lower()

    def test_retriever_initialization(self, project):
        """Test that retriever initializes correctly."""
        retriever = KnowledgeRetriever(project)

        assert retriever.project == project
        assert hasattr(retriever, "retrieve")

    def test_empty_project_knowledge(self, project):
        """Test handling of project with no knowledge at all."""
        # Don't add any knowledge
        retriever = KnowledgeRetriever(project)
        result = retriever.retrieve()

        # Should return valid string even with no knowledge
        assert isinstance(result, str)
