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


class ConfidenceRangeFilter(admin.SimpleListFilter):
    """Filter learnings by confidence score ranges."""

    title = "confidence range"
    parameter_name = "confidence_range"

    def lookups(self, request, model_admin):
        return [
            ("high", "High (0.8 - 1.0)"),
            ("medium", "Medium (0.5 - 0.8)"),
            ("low", "Low (0.0 - 0.5)"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "high":
            return queryset.filter(confidence_score__gte=0.8)
        elif self.value() == "medium":
            return queryset.filter(confidence_score__gte=0.5, confidence_score__lt=0.8)
        elif self.value() == "low":
            return queryset.filter(confidence_score__lt=0.5)
        return queryset


@admin.register(AgentLearning)
class AgentLearningAdmin(admin.ModelAdmin):
    """Admin interface for AgentLearning model with curation workflow."""

    list_display = [
        "description_short",
        "project",
        "category",
        "confidence_badge",
        "times_applied",
        "is_active",
        "promoted_to",
        "created_at",
    ]
    list_filter = ["project", "category", "is_active", "promoted_to", ConfidenceRangeFilter]
    search_fields = ["description", "original_error", "original_sql", "corrected_sql"]
    actions = [
        "approve_learnings",
        "reject_learnings",
        "promote_to_business_rule",
        "promote_to_verified_query",
        "increase_confidence",
        "decrease_confidence",
    ]

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

    @admin.display(description="Confidence")
    def confidence_badge(self, obj):
        score = obj.confidence_score
        if score >= 0.8:
            color = "green"
        elif score >= 0.5:
            color = "orange"
        else:
            color = "red"
        return f'<span style="color: {color}; font-weight: bold;">{score:.0%}</span>'

    confidence_badge.allow_tags = True

    @admin.action(description="Approve learnings (activate + increase confidence)")
    def approve_learnings(self, request, queryset):
        count = 0
        for learning in queryset:
            learning.is_active = True
            learning.confidence_score = min(1.0, learning.confidence_score + 0.1)
            learning.save(update_fields=["is_active", "confidence_score"])
            count += 1
        self.message_user(request, f"Approved {count} learnings")

    @admin.action(description="Reject learnings (deactivate)")
    def reject_learnings(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Rejected {count} learnings")

    @admin.action(description="Increase confidence (+10%)")
    def increase_confidence(self, request, queryset):
        count = 0
        for learning in queryset:
            learning.increase_confidence(0.1)
            count += 1
        self.message_user(request, f"Increased confidence for {count} learnings")

    @admin.action(description="Decrease confidence (-10%)")
    def decrease_confidence(self, request, queryset):
        count = 0
        for learning in queryset:
            learning.decrease_confidence(0.1)
            count += 1
        self.message_user(request, f"Decreased confidence for {count} learnings")

    @admin.action(description="Promote to Business Rule")
    def promote_to_business_rule(self, request, queryset):
        count = 0
        for learning in queryset:
            if learning.promoted_to:
                continue  # Skip already promoted
            try:
                learning.promote_to_business_rule(user=request.user)
                count += 1
            except ValueError as e:
                self.message_user(request, f"Error promoting learning: {e}", level="error")
        self.message_user(request, f"Promoted {count} learnings to Business Rules")

    @admin.action(description="Promote to Verified Query")
    def promote_to_verified_query(self, request, queryset):
        count = 0
        skipped = 0
        for learning in queryset:
            if learning.promoted_to:
                skipped += 1
                continue
            if not learning.corrected_sql:
                skipped += 1
                continue
            try:
                learning.promote_to_verified_query(user=request.user)
                count += 1
            except ValueError as e:
                self.message_user(request, f"Error promoting learning: {e}", level="error")
        self.message_user(
            request,
            f"Promoted {count} learnings to Verified Queries (skipped {skipped})",
        )


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
