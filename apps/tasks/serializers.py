from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import Task, TaskActivity, TaskPriority, TaskStatus


class TaskSerializer(serializers.ModelSerializer):
    assigned_to_details = EmployeeListSerializer(source="assigned_to", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.display_name", read_only=True, default=None)
    team_name = serializers.CharField(source="team.name", read_only=True, default=None)

    class Meta:
        model = Task
        fields = [
            "id", "title", "description", "assigned_to", "assigned_to_details",
            "assigned_by", "assigned_by_name", "team", "team_name", "priority",
            "status", "due_date", "completed_at", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "assigned_by", "assigned_by_name", "completed_at", "created_at", "updated_at"]


class TaskStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=TaskStatus.choices)


class TaskAssignSerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField()


class TaskActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.display_name", read_only=True, default=None)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = TaskActivity
        fields = [
            "id",
            "task",
            "task_title",
            "actor",
            "actor_name",
            "action",
            "old_value",
            "new_value",
            "description",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields
