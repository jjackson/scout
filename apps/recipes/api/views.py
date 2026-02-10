"""
API views for recipe management.

Provides endpoints for CRUD operations on recipes, running recipes,
and viewing run history.
"""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.api.permissions import ProjectPermissionMixin
from apps.recipes.models import Recipe, RecipeRun, RecipeRunStatus

from .serializers import (
    RecipeDetailSerializer,
    RecipeListSerializer,
    RecipeRunSerializer,
    RecipeUpdateSerializer,
    RunRecipeSerializer,
)

logger = logging.getLogger(__name__)


class RecipePermissionMixin(ProjectPermissionMixin):
    """
    Extended permission mixin for recipe operations.

    Adds recipe-specific helper methods on top of base project permissions.
    """

    def get_recipe(self, project, recipe_id):
        """Retrieve a recipe by ID within a project."""
        return get_object_or_404(
            Recipe.objects.prefetch_related("steps"),
            pk=recipe_id,
            project=project,
        )


class RecipeListView(RecipePermissionMixin, APIView):
    """
    List all recipes for a project.

    GET /api/projects/{project_id}/recipes/
        Returns list of recipes for the project.
        Requires project membership.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """List all recipes for a project."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        recipes = Recipe.objects.filter(project=project).prefetch_related(
            "steps", "runs"
        )
        serializer = RecipeListSerializer(recipes, many=True)
        return Response(serializer.data)


class RecipeDetailView(RecipePermissionMixin, APIView):
    """
    Retrieve, update, or delete a recipe.

    GET /api/projects/{project_id}/recipes/{recipe_id}/
        Returns recipe details with steps. Requires project membership.

    PUT /api/projects/{project_id}/recipes/{recipe_id}/
        Updates recipe and its steps. Requires project membership.

    DELETE /api/projects/{project_id}/recipes/{recipe_id}/
        Deletes recipe. Requires admin role.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, recipe_id):
        """Retrieve a recipe by ID."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        recipe = self.get_recipe(project, recipe_id)
        serializer = RecipeDetailSerializer(recipe)
        return Response(serializer.data)

    def put(self, request, project_id, recipe_id):
        """Update a recipe."""
        project = self.get_project(project_id)

        # Require analyst or admin permission to edit recipes
        can_edit, error_response = self.check_edit_permission(request, project)
        if not can_edit:
            return error_response

        recipe = self.get_recipe(project, recipe_id)
        serializer = RecipeUpdateSerializer(
            recipe,
            data=request.data,
            partial=True,
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        # Return the updated recipe with full details
        response_serializer = RecipeDetailSerializer(recipe)
        return Response(response_serializer.data)

    def delete(self, request, project_id, recipe_id):
        """Delete a recipe."""
        project = self.get_project(project_id)

        is_admin, error_response = self.check_admin_permission(request, project)
        if not is_admin:
            return error_response

        recipe = self.get_recipe(project, recipe_id)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeRunView(RecipePermissionMixin, APIView):
    """
    Run a recipe with provided variable values.

    POST /api/projects/{project_id}/recipes/{recipe_id}/run/
        Executes the recipe with provided variables.
        Creates a RecipeRun record with status "pending".
        Actual execution would be handled asynchronously by the agent system.
        Requires project membership.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, recipe_id):
        """Run a recipe."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        recipe = self.get_recipe(project, recipe_id)

        serializer = RunRecipeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        variables = serializer.validated_data.get("variables", {})

        # Validate variables against recipe definition
        validation_errors = recipe.validate_variable_values(variables)
        if validation_errors:
            return Response(
                {"error": "Variable validation failed", "details": validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a pending run record
        run = RecipeRun.objects.create(
            recipe=recipe,
            status=RecipeRunStatus.PENDING,
            variable_values=variables,
            run_by=request.user,
            started_at=timezone.now(),
        )

        # TODO: Trigger async execution via the agent system
        # For now, we just return the pending run record

        serializer = RecipeRunSerializer(run)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RecipeRunHistoryView(RecipePermissionMixin, APIView):
    """
    List run history for a recipe.

    GET /api/projects/{project_id}/recipes/{recipe_id}/runs/
        Returns list of recipe runs ordered by creation date (newest first).
        Requires project membership.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id, recipe_id):
        """List run history for a recipe."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        recipe = self.get_recipe(project, recipe_id)
        runs = RecipeRun.objects.filter(recipe=recipe).order_by("-created_at")

        serializer = RecipeRunSerializer(runs, many=True)
        return Response(serializer.data)
