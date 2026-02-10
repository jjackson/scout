"""
URL configuration for projects app.
"""
from django.urls import path

from apps.projects.views import ProjectListView

app_name = "projects"

urlpatterns = [
    path("", ProjectListView.as_view(), name="project-list"),
]
