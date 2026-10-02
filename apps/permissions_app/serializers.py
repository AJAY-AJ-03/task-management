from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import PermissionRequest


class PermissionRequestSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.display_name", read_only=True, default=None)

    class Meta:
        model = PermissionRequest
        fields = [
            "id", "employee", "employee_details", "date", "start_time", "end_time",
            "duration_minutes", "reason", "status", "approved_by", "approved_by_name",
            "approved_at", "rejection_reason", "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "duration_minutes", "status", "approved_by", "approved_by_name",
            "approved_at", "rejection_reason", "created_at", "updated_at"
        ]


class PermissionCreateSerializer(serializers.Serializer):
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    reason = serializers.CharField()


class PermissionRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
