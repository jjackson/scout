"""
URL configuration for Scout data agent platform.
"""
from django.contrib import admin
from django.urls import include, path

from apps.projects.views import health_check

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/auth/", include("apps.chat.auth_urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/knowledge/", include("apps.knowledge.urls")),
    path("api/artifacts/", include("apps.artifacts.urls")),
    path("api/recipes/", include("apps.recipes.urls")),
]
