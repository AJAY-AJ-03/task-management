from rest_framework import serializers
from .models import Escalation, EscalationStatus


class EscalationSerializer(serializers.ModelSerializer):
    raised_by_code = serializers.CharField(source="raised_by.employee_code", read_only=True)
    raised_by_name = serializers.CharField(source="raised_by.user.display_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.display_name", read_only=True, default=None)
    related_task_title = serializers.CharField(source="related_task.title", read_only=True, default=None)

    class Meta:
        model = Escalation
        fields = [
            "id",
            "title",
            "description",
            "priority",
            "status",
            "raised_by",
            "raised_by_code",
            "raised_by_name",
            "assigned_to",
            "assigned_to_name",
            "related_task",
            "related_task_title",
            "attachment",
            "resolution_notes",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "raised_by",
            "raised_by_code",
            "raised_by_name",
            "assigned_to_name",
            "related_task_title",
            "resolved_at",
            "created_at",
            "updated_at",
        ]


class EscalationAssignSerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField(help_text="User ID of manager/TL to assign escalation to")


class EscalationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=EscalationStatus.choices)
    resolution_notes = serializers.CharField(required=False, allow_blank=True, default="")
