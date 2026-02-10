"""
Serializers for knowledge management API.

Provides serializers for CanonicalMetric, BusinessRule, VerifiedQuery,
and AgentLearning models with a unified type field for polymorphic handling.
"""
from rest_framework import serializers

from apps.knowledge.models import (
    AgentLearning,
    BusinessRule,
    CanonicalMetric,
    VerifiedQuery,
)


class CanonicalMetricSerializer(serializers.ModelSerializer):
    """
    Serializer for CanonicalMetric model.

    Includes a type field that returns "metric" for client-side type discrimination.
    """

    type = serializers.SerializerMethodField()

    class Meta:
        model = CanonicalMetric
        fields = [
            "id",
            "type",
            "name",
            "definition",
            "sql_template",
            "unit",
            "owner",
            "caveats",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def get_type(self, obj) -> str:
        """Return the knowledge item type identifier."""
        return "metric"


class BusinessRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for BusinessRule model.

    Includes a type field that returns "rule" for client-side type discrimination.
    """

    type = serializers.SerializerMethodField()

    class Meta:
        model = BusinessRule
        fields = [
            "id",
            "type",
            "title",
            "description",
            "applies_to_tables",
            "applies_to_metrics",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "created_at", "updated_at"]

    def get_type(self, obj) -> str:
        """Return the knowledge item type identifier."""
        return "rule"


class VerifiedQuerySerializer(serializers.ModelSerializer):
    """
    Serializer for VerifiedQuery model.

    Includes a type field that returns "query" for client-side type discrimination.
    """

    type = serializers.SerializerMethodField()

    class Meta:
        model = VerifiedQuery
        fields = [
            "id",
            "type",
            "name",
            "description",
            "sql",
            "tags",
            "tables_used",
            "verified_by",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "type", "verified_by", "verified_at", "created_at", "updated_at"]

    def get_type(self, obj) -> str:
        """Return the knowledge item type identifier."""
        return "query"


class AgentLearningSerializer(serializers.ModelSerializer):
    """
    Serializer for AgentLearning model.

    Includes a type field that returns "learning" for client-side type discrimination.
    """

    type = serializers.SerializerMethodField()

    class Meta:
        model = AgentLearning
        fields = [
            "id",
            "type",
            "description",
            "category",
            "applies_to_tables",
            "original_error",
            "original_sql",
            "corrected_sql",
            "confidence_score",
            "times_applied",
            "is_active",
            "promoted_to",
            "promoted_to_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "type",
            "times_applied",
            "promoted_to",
            "promoted_to_id",
            "created_at",
        ]

    def get_type(self, obj) -> str:
        """Return the knowledge item type identifier."""
        return "learning"


class PromoteLearningSerializer(serializers.Serializer):
    """
    Serializer for promoting an AgentLearning to a BusinessRule or VerifiedQuery.

    Validates the target type and triggers the appropriate promotion method.
    """

    promote_to = serializers.ChoiceField(
        choices=["business_rule", "verified_query"],
        help_text="Target type to promote the learning to.",
    )

    def validate(self, attrs):
        """
        Validate the promotion request.

        Ensures the learning hasn't already been promoted and has
        corrected_sql if promoting to verified_query.
        """
        learning = self.context.get("learning")
        promote_to = attrs.get("promote_to")

        if learning.promoted_to:
            raise serializers.ValidationError(
                f"This learning has already been promoted to {learning.promoted_to}."
            )

        if promote_to == "verified_query" and not learning.corrected_sql:
            raise serializers.ValidationError(
                "Cannot promote to verified query: no corrected SQL available."
            )

        return attrs

    def create(self, validated_data):
        """
        Promote the learning to the specified type.

        Returns the newly created BusinessRule or VerifiedQuery.
        """
        learning = self.context["learning"]
        user = self.context.get("request").user if self.context.get("request") else None
        promote_to = validated_data["promote_to"]

        if promote_to == "business_rule":
            return learning.promote_to_business_rule(user=user)
        else:
            return learning.promote_to_verified_query(user=user)
