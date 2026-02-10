"""
URL configuration for knowledge app.
"""
from django.urls import path

from .api.views import KnowledgeDetailView, KnowledgeListCreateView, PromoteLearningView

app_name = "knowledge"

urlpatterns = [
    path("", KnowledgeListCreateView.as_view(), name="list_create"),
    path("<uuid:item_id>/", KnowledgeDetailView.as_view(), name="detail"),
    path("<uuid:item_id>/promote/", PromoteLearningView.as_view(), name="promote"),
]
