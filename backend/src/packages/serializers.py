"""FR-16 input validation serializers."""

from rest_framework import serializers

from .models import DatasetBinding, NodeType, WorkspaceStatus


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
    orderIndex = serializers.IntegerField(required=False, default=0)
    datasetBinding = serializers.ChoiceField(
        choices=DatasetBinding.choices, required=False, allow_null=True
    )
    bindingCourseId = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    identifiable = serializers.BooleanField(required=False, default=False)
    includeAnswers = serializers.BooleanField(required=False, default=False)


class UpdateNodeSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255, required=False)
    parentId = serializers.IntegerField(required=False, allow_null=True)
    orderIndex = serializers.IntegerField(required=False)
    datasetBinding = serializers.ChoiceField(
        choices=DatasetBinding.choices, required=False, allow_null=True
    )
    bindingCourseId = serializers.IntegerField(required=False, allow_null=True)
    filters = serializers.JSONField(required=False, allow_null=True)
    identifiable = serializers.BooleanField(required=False)
    includeAnswers = serializers.BooleanField(required=False)


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
    targetOrderIndex = serializers.IntegerField()
