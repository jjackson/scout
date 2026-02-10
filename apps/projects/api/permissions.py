"""
Shared permission mixins for project-based API views.

Provides common permission checking methods used across multiple apps.
"""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from apps.projects.models import Project, ProjectMembership, ProjectRole


class ProjectPermissionMixin:
    """
    Mixin providing permission checking for project operations.

    Provides methods to check if a user has access to a project
    and if they have specific role-based permissions.

    Usage:
        class MyView(ProjectPermissionMixin, APIView):
            def get(self, request, project_id):
                project = self.get_project(project_id)

                has_access, error = self.check_project_access(request, project)
                if not has_access:
                    return error

                # ... view logic
    """

    def get_project(self, project_id):
        """
        Retrieve a project by ID with memberships prefetched.

        Args:
            project_id: The project's primary key (UUID)

        Returns:
            Project instance

        Raises:
            Http404: If project doesn't exist
        """
        return get_object_or_404(
            Project.objects.prefetch_related("memberships"),
            pk=project_id,
        )

    def get_user_membership(self, user, project):
        """
        Get the user's membership in a project, if any.

        Args:
            user: The user to check
            project: The project to check membership for

        Returns:
            ProjectMembership instance or None if no membership exists
            (returns None for superusers as they have implicit access)
        """
        if user.is_superuser:
            return None  # Superusers have implicit access
        return ProjectMembership.objects.filter(
            user=user,
            project=project,
        ).first()

    def check_project_access(self, request, project):
        """
        Check if the user has any access to the project.

        All authenticated project members (viewer, analyst, admin) pass this check.

        Args:
            request: The HTTP request
            project: The project to check access for

        Returns:
            tuple: (has_access: bool, error_response: Response or None)
        """
        if request.user.is_superuser:
            return True, None

        membership = self.get_user_membership(request.user, project)
        if membership:
            return True, None

        return False, Response(
            {"error": "You do not have access to this project."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def check_edit_permission(self, request, project):
        """
        Check if the user has edit permission for the project.

        Analysts and admins can edit. Viewers cannot.

        Args:
            request: The HTTP request
            project: The project to check permission for

        Returns:
            tuple: (can_edit: bool, error_response: Response or None)
        """
        if request.user.is_superuser:
            return True, None

        membership = self.get_user_membership(request.user, project)
        if membership and membership.role in (ProjectRole.ANALYST, ProjectRole.ADMIN):
            return True, None

        return False, Response(
            {"error": "You must be an analyst or admin to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def check_admin_permission(self, request, project):
        """
        Check if the user has admin permission for the project.

        Only admins (and superusers) pass this check.

        Args:
            request: The HTTP request
            project: The project to check permission for

        Returns:
            tuple: (is_admin: bool, error_response: Response or None)
        """
        if request.user.is_superuser:
            return True, None

        membership = self.get_user_membership(request.user, project)
        if membership and membership.role == ProjectRole.ADMIN:
            return True, None

        return False, Response(
            {"error": "You must be a project admin to perform this action."},
            status=status.HTTP_403_FORBIDDEN,
        )
