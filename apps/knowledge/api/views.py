"""
API views for knowledge management.

Provides endpoints for listing, creating, updating, and deleting knowledge items
(CanonicalMetric, BusinessRule, VerifiedQuery, AgentLearning) with a unified
interface and type-specific operations.
"""
import logging

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.knowledge.models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    VerifiedQuery,
)
from apps.projects.api.permissions import ProjectPermissionMixin

from .serializers import (
    AgentLearningSerializer,
    BusinessRuleSerializer,
    CanonicalMetricSerializer,
    PromoteLearningSerializer,
    VerifiedQuerySerializer,
)

logger = logging.getLogger(__name__)

# Pagination settings
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


# Mapping of type names to models and serializers
KNOWLEDGE_TYPES = {
    "metric": {
        "model": CanonicalMetric,
        "serializer": CanonicalMetricSerializer,
        "search_fields": ["name", "definition", "sql_template"],
    },
    "rule": {
        "model": BusinessRule,
        "serializer": BusinessRuleSerializer,
        "search_fields": ["title", "description"],
    },
    "query": {
        "model": VerifiedQuery,
        "serializer": VerifiedQuerySerializer,
        "search_fields": ["name", "description", "sql"],
    },
    "learning": {
        "model": AgentLearning,
        "serializer": AgentLearningSerializer,
        "search_fields": ["description", "original_error", "original_sql", "corrected_sql"],
    },
}


class KnowledgeListCreateView(ProjectPermissionMixin, APIView):
    """
    List all knowledge items or create a new one.

    GET /api/projects/{project_id}/knowledge/
        Returns list of all knowledge items (metrics, rules, queries, learnings).
        Supports filtering by type and text search.

        Query parameters:
        - type: Filter by knowledge type (metric, rule, query, learning)
        - search: Text search across relevant fields

    POST /api/projects/{project_id}/knowledge/
        Creates a new knowledge item. The type field in the request body
        determines which model to create.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        """List all knowledge items for a project with pagination."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        # Get filter parameters
        type_filter = request.query_params.get("type")
        search_query = request.query_params.get("search", "").strip()

        # Get pagination parameters
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = min(
                MAX_PAGE_SIZE,
                max(1, int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))),
            )
        except (ValueError, TypeError):
            page_size = DEFAULT_PAGE_SIZE

        # Determine which types to query
        if type_filter and type_filter in KNOWLEDGE_TYPES:
            types_to_query = [type_filter]
        else:
            types_to_query = list(KNOWLEDGE_TYPES.keys())

        # Collect all items
        all_items = []

        for type_name in types_to_query:
            type_config = KNOWLEDGE_TYPES[type_name]
            model = type_config["model"]
            serializer_class = type_config["serializer"]

            # Base queryset filtered by project
            queryset = model.objects.filter(project=project)

            # Apply text search if provided
            if search_query:
                search_q = Q()
                for field in type_config["search_fields"]:
                    search_q |= Q(**{f"{field}__icontains": search_query})
                queryset = queryset.filter(search_q)

            # Serialize and add type info
            serializer = serializer_class(queryset, many=True)
            all_items.extend(serializer.data)

        # Sort by created_at descending (most recent first)
        all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # Apply pagination
        total_count = len(all_items)
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_items = all_items[start_index:end_index]

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return Response({
            "results": paginated_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1,
            },
        })

    def post(self, request, project_id):
        """Create a new knowledge item."""
        project = self.get_project(project_id)

        can_edit, error_response = self.check_edit_permission(request, project)
        if not can_edit:
            return error_response

        # Determine the type from request body
        item_type = request.data.get("type")
        if not item_type or item_type not in KNOWLEDGE_TYPES:
            return Response(
                {"error": f"Invalid or missing type. Must be one of: {', '.join(KNOWLEDGE_TYPES.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        type_config = KNOWLEDGE_TYPES[item_type]
        serializer_class = type_config["serializer"]

        # Create the item
        serializer = serializer_class(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Save with project association
        instance = serializer.save(project=project)

        # Handle type-specific user associations
        if item_type == "metric":
            instance.updated_by = request.user
            instance.save(update_fields=["updated_by"])
        elif item_type == "rule":
            instance.created_by = request.user
            instance.save(update_fields=["created_by"])
        elif item_type == "query":
            from django.utils import timezone
            instance.verified_by = request.user
            instance.verified_at = timezone.now()
            instance.save(update_fields=["verified_by", "verified_at"])
        elif item_type == "learning":
            instance.discovered_by_user = request.user
            instance.save(update_fields=["discovered_by_user"])

        # Return the created item
        response_serializer = serializer_class(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class KnowledgeDetailView(ProjectPermissionMixin, APIView):
    """
    Retrieve, update, or delete a knowledge item.

    GET /api/projects/{project_id}/knowledge/{item_id}/
        Returns knowledge item details. Searches across all knowledge types.

    PUT /api/projects/{project_id}/knowledge/{item_id}/
        Updates a knowledge item. Requires editor or admin role.

    DELETE /api/projects/{project_id}/knowledge/{item_id}/
        Deletes a knowledge item. Requires editor or admin role.
    """

    permission_classes = [IsAuthenticated]

    def _find_item(self, project, item_id):
        """
        Find a knowledge item by ID across all types.

        Returns:
            tuple: (item, type_name, serializer_class) or (None, None, None)
        """
        for type_name, type_config in KNOWLEDGE_TYPES.items():
            model = type_config["model"]
            try:
                item = model.objects.get(pk=item_id, project=project)
                return item, type_name, type_config["serializer"]
            except model.DoesNotExist:
                continue
        return None, None, None

    def get(self, request, project_id, item_id):
        """Retrieve a knowledge item by ID."""
        project = self.get_project(project_id)

        has_access, error_response = self.check_project_access(request, project)
        if not has_access:
            return error_response

        item, type_name, serializer_class = self._find_item(project, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = serializer_class(item)
        return Response(serializer.data)

    def put(self, request, project_id, item_id):
        """Update a knowledge item."""
        project = self.get_project(project_id)

        can_edit, error_response = self.check_edit_permission(request, project)
        if not can_edit:
            return error_response

        item, type_name, serializer_class = self._find_item(project, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = serializer_class(
            item,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        instance = serializer.save()

        # Update the updated_by field for types that have it
        if type_name == "metric":
            instance.updated_by = request.user
            instance.save(update_fields=["updated_by"])

        return Response(serializer.data)

    def delete(self, request, project_id, item_id):
        """Delete a knowledge item."""
        project = self.get_project(project_id)

        can_edit, error_response = self.check_edit_permission(request, project)
        if not can_edit:
            return error_response

        item, type_name, serializer_class = self._find_item(project, item_id)
        if not item:
            return Response(
                {"error": "Knowledge item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PromoteLearningView(ProjectPermissionMixin, APIView):
    """
    Promote an AgentLearning to a BusinessRule or VerifiedQuery.

    POST /api/projects/{project_id}/knowledge/{item_id}/promote/
        Promotes the learning to the specified type.
        Creates a new BusinessRule or VerifiedQuery based on the learning,
        marks the learning as promoted, and deactivates it.

        Request body:
        - promote_to: "business_rule" or "verified_query"
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, item_id):
        """Promote an AgentLearning to a BusinessRule or VerifiedQuery."""
        project = self.get_project(project_id)

        can_edit, error_response = self.check_edit_permission(request, project)
        if not can_edit:
            return error_response

        # Find the learning
        try:
            learning = AgentLearning.objects.get(pk=item_id, project=project)
        except AgentLearning.DoesNotExist:
            return Response(
                {"error": "Agent learning not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Validate and promote
        serializer = PromoteLearningSerializer(
            data=request.data,
            context={"learning": learning, "request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        promoted_item = serializer.save()

        # Return the promoted item with appropriate serializer
        promote_to = request.data.get("promote_to")
        if promote_to == "business_rule":
            response_serializer = BusinessRuleSerializer(promoted_item)
        else:
            response_serializer = VerifiedQuerySerializer(promoted_item)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
