from rest_framework import serializers
from .models import SOP


class SOPSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    process_name = serializers.CharField(source="process.name", read_only=True, default=None)
    team_name = serializers.CharField(source="team.name", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True, default=None)
    updated_by_name = serializers.CharField(source="updated_by.display_name", read_only=True, default=None)

    class Meta:
        model = SOP
        fields = [
            "id",
            "title",
            "content",
            "category",
            "department",
            "department_name",
            "process",
            "process_name",
            "team",
            "team_name",
            "attachment",
            "status",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "department_name",
            "process_name",
            "team_name",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "created_at",
            "updated_at",
        ]
