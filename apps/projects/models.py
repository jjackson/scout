"""
Core project models for Scout data agent platform.

Defines Project, ProjectMembership, SavedQuery, and ConversationLog models.
"""
import uuid

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


# Validator for database schema names to prevent SQL injection
schema_validator = RegexValidator(
    regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$',
    message='Invalid schema name format. Must start with a letter or underscore, and contain only letters, numbers, and underscores.'
)


class Project(models.Model):
    """
    Represents a data project with its own database scope and agent configuration.

    Each project connects to a specific PostgreSQL database/schema and has its own
    agent configuration, system prompt, and data dictionary.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    # Database connection (encrypted at rest)
    db_host = models.CharField(max_length=255)
    db_port = models.IntegerField(default=5432)
    db_name = models.CharField(max_length=255)
    db_schema = models.CharField(
        max_length=255,
        default="public",
        validators=[schema_validator],
    )
    # Encrypted fields - store the encrypted connection credentials
    _db_user = models.BinaryField(db_column="db_user")
    _db_password = models.BinaryField(db_column="db_password")

    # Optional: restrict which tables the agent can see
    # Empty list = all tables in schema are visible
    allowed_tables = models.JSONField(default=list, blank=True)
    # Tables to explicitly exclude (useful when allowed_tables is empty/all)
    excluded_tables = models.JSONField(default=list, blank=True)

    # Agent configuration
    system_prompt = models.TextField(
        blank=True,
        help_text="Project-specific system prompt. Merged with the base agent prompt.",
    )
    max_rows_per_query = models.IntegerField(
        default=500,
        help_text="Maximum rows the SQL tool will return per query.",
    )
    max_query_timeout_seconds = models.IntegerField(
        default=30,
        help_text="Query execution timeout.",
    )
    llm_model = models.CharField(
        max_length=100,
        default="claude-sonnet-4-5-20250929",
        help_text="LLM model identifier for the agent.",
    )

    # Data dictionary (cached, regenerated on demand)
    data_dictionary = models.JSONField(
        null=True,
        blank=True,
        help_text="Auto-generated schema documentation. Regenerated via management command.",
    )
    data_dictionary_generated_at = models.DateTimeField(null=True, blank=True)

    # Database role for read-only access (created by setup_project_db.py)
    readonly_role = models.CharField(
        max_length=100,
        blank=True,
        help_text="PostgreSQL role name for read-only access to project database.",
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_projects",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def _get_fernet(self):
        """Get Fernet instance for encryption/decryption."""
        key = settings.DB_CREDENTIAL_KEY
        if not key:
            raise ValueError("DB_CREDENTIAL_KEY is not set in settings")
        return Fernet(key.encode() if isinstance(key, str) else key)

    @property
    def db_user(self):
        """Decrypt and return the database username."""
        if not self._db_user:
            return ""
        f = self._get_fernet()
        return f.decrypt(bytes(self._db_user)).decode()

    @db_user.setter
    def db_user(self, value):
        """Encrypt and store the database username."""
        if not value:
            self._db_user = b""
            return
        f = self._get_fernet()
        self._db_user = f.encrypt(value.encode())

    @property
    def db_password(self):
        """Decrypt and return the database password."""
        if not self._db_password:
            return ""
        f = self._get_fernet()
        return f.decrypt(bytes(self._db_password)).decode()

    @db_password.setter
    def db_password(self, value):
        """Encrypt and store the database password."""
        if not value:
            self._db_password = b""
            return
        f = self._get_fernet()
        self._db_password = f.encrypt(value.encode())

    def get_connection_params(self) -> dict:
        """Return connection params for psycopg2/SQLAlchemy."""
        return {
            "host": self.db_host,
            "port": self.db_port,
            "dbname": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "options": f"-c search_path={self.db_schema},public -c statement_timeout={self.max_query_timeout_seconds * 1000}",
        }


class ProjectRole(models.TextChoices):
    """Role choices for project membership."""

    VIEWER = "viewer", "Viewer"  # Can chat with agent, view results
    ANALYST = "analyst", "Analyst"  # Can chat, export data, create saved queries
    ADMIN = "admin", "Admin"  # Full project config access


class ProjectMembership(models.Model):
    """
    Links users to projects with role-based access.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_memberships",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=ProjectRole.choices, default=ProjectRole.VIEWER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "project"]

    def __str__(self):
        return f"{self.user} - {self.project} ({self.role})"


class SavedQuery(models.Model):
    """
    Queries that users can save and re-run.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="saved_queries")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sql = models.TextField()
    is_shared = models.BooleanField(default=False, help_text="Visible to all project members")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name_plural = "Saved queries"
        indexes = [
            models.Index(fields=["project", "-updated_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.project.name})"


class ConversationLog(models.Model):
    """
    Stores conversation history for audit and memory.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="conversations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    thread_id = models.CharField(max_length=255, db_index=True)
    messages = models.JSONField(default=list)
    # Track which queries were executed in this conversation
    queries_executed = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["project", "user", "-created_at"]),
        ]

    def __str__(self):
        return f"Conversation {self.thread_id} ({self.project.name})"
