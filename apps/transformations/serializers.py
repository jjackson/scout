from rest_framework import serializers

from .models import TransformationAsset, TransformationAssetRun, TransformationRun


class TransformationAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransformationAsset
        fields = [
            "id",
            "name",
            "description",
            "scope",
            "tenant",
            "workspace",
            "sql_content",
            "replaces",
            "test_yaml",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class TransformationAssetRunSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)

    class Meta:
        model = TransformationAssetRun
        fields = [
            "id",
            "asset",
            "asset_name",
            "status",
            "duration_ms",
            "logs",
            "test_results",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields


class TransformationRunSerializer(serializers.ModelSerializer):
    asset_runs = TransformationAssetRunSerializer(many=True, read_only=True)

    class Meta:
        model = TransformationRun
        fields = [
            "id",
            "tenant",
            "workspace",
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "asset_runs",
        ]
        read_only_fields = fields


class LineageResponseSerializer(serializers.Serializer):
    """Read-only serializer for lineage chain entries."""

    name = serializers.CharField()
    scope = serializers.CharField()
    description = serializers.CharField()
