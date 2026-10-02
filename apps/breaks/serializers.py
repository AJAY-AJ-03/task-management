from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import BreakRecord, BreakType


class BreakTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BreakType
        fields = ["id", "name", "duration_minutes", "is_paid", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class BreakRecordSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    break_type_name = serializers.CharField(source="break_type.name", read_only=True)

    class Meta:
        model = BreakRecord
        fields = [
            "id", "employee", "employee_details", "break_type", "break_type_name",
            "attendance", "start_time", "end_time", "duration_seconds", "status",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "duration_seconds", "created_at", "updated_at"]


class StartBreakSerializer(serializers.Serializer):
    break_type_id = serializers.IntegerField()
    start_time = serializers.DateTimeField(required=False, allow_null=True)


class EndBreakSerializer(serializers.Serializer):
    end_time = serializers.DateTimeField(required=False, allow_null=True)
