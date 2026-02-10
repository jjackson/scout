"""URL configuration for auth endpoints."""
from django.urls import path

from apps.chat.views import csrf_view, login_view, logout_view, me_view

app_name = "auth"

urlpatterns = [
    path("csrf/", csrf_view, name="csrf"),
    path("me/", me_view, name="me"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]
