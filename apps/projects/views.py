"""
Views for projects app.
"""
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import ProjectMembership


def health_check(request):
    """
    Simple health check endpoint that returns a 200 JSON response.
    Used by Docker health checks and load balancers.
    """
    return JsonResponse({"status": "ok"})


class ProjectListView(APIView):
    """GET /api/projects/ -- list projects the current user has access to."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            ProjectMembership.objects.filter(user=request.user)
            .select_related("project")
            .order_by("project__name")
        )
        data = [
            {
                "id": str(m.project.id),
                "name": m.project.name,
                "slug": m.project.slug,
                "description": m.project.description,
                "role": m.role,
            }
            for m in memberships
            if m.project.is_active
        ]
        return Response(data)
