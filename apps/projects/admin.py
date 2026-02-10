"""
Admin configuration for Project models.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Project, ProjectMembership


class ProjectMembershipInline(admin.TabularInline):
    """Inline admin for project memberships."""

    model = ProjectMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin interface for Project model."""

    list_display = [
        "name",
        "slug",
        "db_host",
        "db_name",
        "db_schema",
        "member_count",
        "has_data_dictionary",
        "created_at",
    ]
    list_filter = ["created_at", "llm_model"]
    search_fields = ["name", "slug", "description"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "data_dictionary_generated_at",
        "data_dictionary_status",
    ]
    autocomplete_fields = ["created_by"]
    inlines = [ProjectMembershipInline]
    actions = ["regenerate_data_dictionary"]

    fieldsets = (
        (None, {"fields": ("id", "name", "slug", "description")}),
        (
            "Database Connection",
            {
                "fields": (
                    "db_host",
                    "db_port",
                    "db_name",
                    "db_schema",
                    "db_user_input",
                    "db_password_input",
                ),
                "description": "Database credentials are encrypted at rest.",
            },
        ),
        (
            "Table Access Control",
            {
                "fields": ("allowed_tables", "excluded_tables"),
                "description": "Control which tables the agent can access. Empty allowed_tables means all tables.",
            },
        ),
        (
            "Agent Configuration",
            {
                "fields": (
                    "system_prompt",
                    "max_rows_per_query",
                    "max_query_timeout_seconds",
                    "llm_model",
                ),
            },
        ),
        (
            "Data Dictionary",
            {
                "fields": (
                    "data_dictionary_status",
                    "data_dictionary_generated_at",
                ),
                "description": "Run 'python manage.py generate_data_dictionary --project-slug <slug>' to regenerate.",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Add custom form fields for password input."""
        form = super().get_form(request, obj, **kwargs)
        return form

    def get_fieldsets(self, request, obj=None):
        """Customize fieldsets based on whether we're adding or editing."""
        fieldsets = super().get_fieldsets(request, obj)
        return fieldsets

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.memberships.count()

    @admin.display(description="Data Dictionary", boolean=True)
    def has_data_dictionary(self, obj):
        return obj.data_dictionary is not None

    @admin.display(description="Data Dictionary Status")
    def data_dictionary_status(self, obj):
        if obj.data_dictionary:
            table_count = len(obj.data_dictionary.get("tables", {}))
            return format_html(
                '<span style="color: green;">✓ Generated</span> ({} tables)',
                table_count,
            )
        return format_html('<span style="color: orange;">Not generated</span>')

    # Custom handling for encrypted fields - using form field prefixes
    def save_model(self, request, obj, form, change):
        """Handle encrypted field saving."""
        # Check if db_user or db_password were provided in the form
        if "db_user_input" in form.data and form.data["db_user_input"]:
            obj.db_user = form.data["db_user_input"]
        if "db_password_input" in form.data and form.data["db_password_input"]:
            obj.db_password = form.data["db_password_input"]
        super().save_model(request, obj, form, change)

    @admin.action(description="Regenerate data dictionary for selected projects")
    def regenerate_data_dictionary(self, request, queryset):
        """Admin action to regenerate data dictionaries."""
        from django.contrib import messages
        from .services.data_dictionary import DataDictionaryGenerator

        success_count = 0
        error_count = 0

        for project in queryset:
            try:
                generator = DataDictionaryGenerator(project)
                generator.generate()
                success_count += 1
            except Exception as e:
                error_count += 1
                self.message_user(
                    request,
                    f"Error generating dictionary for {project.name}: {e}",
                    messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                f"Successfully regenerated data dictionary for {success_count} project(s).",
                messages.SUCCESS,
            )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    """Admin interface for ProjectMembership model."""

    list_display = ["user", "project", "role", "created_at"]
    list_filter = ["role", "created_at", "project"]
    search_fields = ["user__email", "project__name"]
    autocomplete_fields = ["user", "project"]


