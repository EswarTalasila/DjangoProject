"""FR-16 input validation serializers."""

from rest_framework import serializers

from .models import DatasetBinding, NodeSourceType, NodeType, WorkspaceStatus


class CreateWorkspaceSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    scopeCourseId = serializers.IntegerField(required=False, allow_null=True)


class UpdateWorkspaceSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=WorkspaceStatus.choices, required=False)


class AddNodeSerializer(serializers.Serializer):
    parentId = serializers.IntegerField(required=False, allow_null=True)
    nodeType = serializers.ChoiceField(choices=NodeType.choices)
    label = serializers.CharField(max_length=255)
    orderIndex = serializers.IntegerField(required=False, default=0, min_value=0)
    datasetBinding = serializers.ChoiceField(
        choices=DatasetBinding.choices, required=False, allow_null=True
    )
    bindingCourseId = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    identifiable = serializers.BooleanField(required=False, default=False)
    includeAnswers = serializers.BooleanField(required=False, default=False)
    sourceType = serializers.ChoiceField(
        choices=NodeSourceType.choices, required=False, default=NodeSourceType.LIVE
    )
    snapshotId = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        source_type = attrs.get("sourceType", NodeSourceType.LIVE)
        snapshot_id = attrs.get("snapshotId")
        node_type = attrs.get("nodeType")

        if source_type == NodeSourceType.SNAPSHOT:
            if node_type != NodeType.FILE:
                raise serializers.ValidationError("SNAPSHOT source type is only valid for FILE nodes.")
            if snapshot_id is None:
                raise serializers.ValidationError("snapshotId is required when sourceType is SNAPSHOT.")

        return attrs


class UpdateNodeSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255, required=False)
    parentId = serializers.IntegerField(required=False, allow_null=True)
    orderIndex = serializers.IntegerField(required=False, min_value=0)
    datasetBinding = serializers.ChoiceField(
        choices=DatasetBinding.choices, required=False, allow_null=True
    )
    bindingCourseId = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    identifiable = serializers.BooleanField(required=False)
    includeAnswers = serializers.BooleanField(required=False)
    sourceType = serializers.ChoiceField(choices=NodeSourceType.choices, required=False)
    snapshotId = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        source_type = attrs.get("sourceType")
        if source_type == NodeSourceType.SNAPSHOT and attrs.get("snapshotId") is None:
            raise serializers.ValidationError("snapshotId must be provided when sourceType is SNAPSHOT.")
        return attrs


class ValidateWorkspaceSerializer(serializers.Serializer):
    strictMode = serializers.BooleanField(required=False, default=True)
    snapshotId = serializers.IntegerField(required=False, allow_null=True)


class BuildWorkspaceSerializer(serializers.Serializer):
    strictMode = serializers.BooleanField(required=False, default=True)
    snapshotId = serializers.IntegerField(required=False, allow_null=True)


class CreateSnapshotSerializer(serializers.Serializer):
    datasetBinding = serializers.ChoiceField(choices=DatasetBinding.choices)
    scopeCourseId = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    includeAnswers = serializers.BooleanField(required=False, default=False)
    identifiable = serializers.BooleanField(required=False, default=False)


class ReorderNodeSerializer(serializers.Serializer):
    movedNodeId = serializers.IntegerField()
    targetParentId = serializers.IntegerField(required=False, allow_null=True)
    targetOrderIndex = serializers.IntegerField(min_value=0)
