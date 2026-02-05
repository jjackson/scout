"""
Admin configuration for Knowledge models.
"""
from django.contrib import admin
from django.utils import timezone

from .models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    EvalRun,
    GoldenQuery,
    TableKnowledge,
    VerifiedQuery,
)


@admin.register(TableKnowledge)
class TableKnowledgeAdmin(admin.ModelAdmin):
    """Admin interface for TableKnowledge model."""

    list_display = ["table_name", "project", "owner", "refresh_frequency", "updated_at"]
    list_filter = ["project", "updated_at"]
    search_fields = ["table_name", "description", "owner"]
    autocomplete_fields = ["project", "updated_by"]

    fieldsets = (
        (None, {"fields": ("project", "table_name")}),
        ("Description", {"fields": ("description", "use_cases")}),
        (
            "Data Quality",
            {"fields": ("data_quality_notes", "owner", "refresh_frequency")},
        ),
        ("Relationships", {"fields": ("related_tables", "column_notes")}),
        (
            "Metadata",
            {
                "fields": ("updated_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CanonicalMetric)
class CanonicalMetricAdmin(admin.ModelAdmin):
    """Admin interface for CanonicalMetric model."""

    list_display = ["name", "project", "unit", "owner", "updated_at"]
    list_filter = ["project", "tags"]
    search_fields = ["name", "definition", "owner"]
    autocomplete_fields = ["project", "updated_by"]

    fieldsets = (
        (None, {"fields": ("project", "name", "unit")}),
        ("Definition", {"fields": ("definition", "sql_template")}),
        ("Ownership", {"fields": ("owner", "caveats", "tags")}),
        (
            "Metadata",
            {
                "fields": ("updated_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(VerifiedQuery)
class VerifiedQueryAdmin(admin.ModelAdmin):
    """Admin interface for VerifiedQuery model."""

    list_display = ["name", "project", "tables_used_display", "verified_by", "verified_at"]
    list_filter = ["project", "verified_at"]
    search_fields = ["name", "description", "sql"]
    autocomplete_fields = ["project", "verified_by"]
    actions = ["mark_as_verified"]

    fieldsets = (
        (None, {"fields": ("project", "name", "description")}),
        ("Query", {"fields": ("sql", "tables_used", "tags")}),
        ("Verification", {"fields": ("verified_by", "verified_at")}),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Tables")
    def tables_used_display(self, obj):
        return ", ".join(obj.tables_used) if obj.tables_used else "-"

    @admin.action(description="Mark selected queries as verified")
    def mark_as_verified(self, request, queryset):
        queryset.update(verified_by=request.user, verified_at=timezone.now())


@admin.register(BusinessRule)
class BusinessRuleAdmin(admin.ModelAdmin):
    """Admin interface for BusinessRule model."""

    list_display = ["title", "project", "applies_to_tables_display", "created_at"]
    list_filter = ["project", "created_at"]
    search_fields = ["title", "description"]
    autocomplete_fields = ["project", "created_by"]

    fieldsets = (
        (None, {"fields": ("project", "title", "description")}),
        ("Scope", {"fields": ("applies_to_tables", "applies_to_metrics", "tags")}),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Tables")
    def applies_to_tables_display(self, obj):
        return ", ".join(obj.applies_to_tables) if obj.applies_to_tables else "All"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AgentLearning)
class AgentLearningAdmin(admin.ModelAdmin):
    """Admin interface for AgentLearning model."""

    list_display = [
        "description_short",
        "project",
        "category",
        "confidence_score",
        "times_applied",
        "is_active",
        "created_at",
    ]
    list_filter = ["project", "category", "is_active", "promoted_to"]
    search_fields = ["description", "original_error"]
    actions = ["promote_to_business_rule", "promote_to_verified_query", "deactivate"]

    fieldsets = (
        (None, {"fields": ("project", "description", "category")}),
        ("Scope", {"fields": ("applies_to_tables",)}),
        (
            "Evidence",
            {
                "fields": ("original_error", "original_sql", "corrected_sql"),
                "classes": ("collapse",),
            },
        ),
        (
            "Lifecycle",
            {"fields": ("confidence_score", "times_applied", "is_active", "promoted_to")},
        ),
        (
            "Source",
            {
                "fields": (
                    "discovered_in_conversation",
                    "discovered_by_user",
                    "created_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["times_applied", "created_at"]

    @admin.display(description="Description")
    def description_short(self, obj):
        return obj.description[:80] + "..." if len(obj.description) > 80 else obj.description

    @admin.action(description="Promote to Business Rule")
    def promote_to_business_rule(self, request, queryset):
        for learning in queryset:
            BusinessRule.objects.create(
                project=learning.project,
                title=f"From Learning: {learning.description[:100]}",
                description=learning.description,
                applies_to_tables=learning.applies_to_tables,
                created_by=request.user,
            )
            learning.promoted_to = "business_rule"
            learning.is_active = False
            learning.save()

    @admin.action(description="Promote to Verified Query")
    def promote_to_verified_query(self, request, queryset):
        for learning in queryset:
            if learning.corrected_sql:
                VerifiedQuery.objects.create(
                    project=learning.project,
                    name=f"From Learning: {learning.description[:100]}",
                    description=learning.description,
                    sql=learning.corrected_sql,
                    tables_used=learning.applies_to_tables,
                    verified_by=request.user,
                    verified_at=timezone.now(),
                )
                learning.promoted_to = "verified_query"
                learning.is_active = False
                learning.save()

    @admin.action(description="Deactivate selected learnings")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(GoldenQuery)
class GoldenQueryAdmin(admin.ModelAdmin):
    """Admin interface for GoldenQuery model."""

    list_display = ["question_short", "project", "difficulty", "comparison_mode", "created_at"]
    list_filter = ["project", "difficulty", "comparison_mode"]
    search_fields = ["question", "expected_sql"]
    autocomplete_fields = ["project", "created_by"]

    fieldsets = (
        (None, {"fields": ("project", "question")}),
        ("Expected", {"fields": ("expected_sql", "expected_result")}),
        ("Comparison", {"fields": ("comparison_mode", "tolerance")}),
        ("Categorization", {"fields": ("difficulty", "tags")}),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["created_at"]

    @admin.display(description="Question")
    def question_short(self, obj):
        return obj.question[:80] + "..." if len(obj.question) > 80 else obj.question

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EvalRun)
class EvalRunAdmin(admin.ModelAdmin):
    """Admin interface for EvalRun model."""

    list_display = [
        "project",
        "model_used",
        "total_queries",
        "passed",
        "failed",
        "accuracy_display",
        "started_at",
    ]
    list_filter = ["project", "model_used", "started_at"]
    readonly_fields = [
        "id",
        "model_used",
        "knowledge_snapshot",
        "total_queries",
        "passed",
        "failed",
        "errored",
        "accuracy",
        "results",
        "started_at",
        "completed_at",
        "triggered_by",
    ]

    @admin.display(description="Accuracy")
    def accuracy_display(self, obj):
        return f"{obj.accuracy:.1%}"
