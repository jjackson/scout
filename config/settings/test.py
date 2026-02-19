"""
Django test settings for Scout data agent platform.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Use faster password hasher in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use PostgreSQL test database to match production and catch DB-specific issues.
# Parse DATABASE_URL from .env as fallback for individual vars (CI sets them explicitly).
_db_url = env.db_url("DATABASE_URL", default=None)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("TEST_DATABASE_NAME", default="scout_test"),
        "USER": env("DATABASE_USER", default=_db_url["USER"] if _db_url else "postgres"),
        "PASSWORD": env(
            "DATABASE_PASSWORD", default=_db_url["PASSWORD"] if _db_url else ""
        ),
        "HOST": env("DATABASE_HOST", default=_db_url["HOST"] if _db_url else "localhost"),
        "PORT": env("DATABASE_PORT", default=str(_db_url["PORT"]) if _db_url else "5432"),
    }
}

# Disable email sending in tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Use a test encryption key (valid Fernet key)
DB_CREDENTIAL_KEY = "uHcVl3o7sAzBTV0ECblIGcB4imVnoutulGMF-dNsUoM="
