"""URL configuration for chat app (streaming endpoint)."""
from django.urls import path

from apps.chat.views import chat_view

app_name = "chat"

urlpatterns = [
    path("", chat_view, name="chat"),
]
