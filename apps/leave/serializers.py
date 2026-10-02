from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "name", "description", "default_days", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id", "employee", "employee_details", "leave_type", "leave_type_name",
            "year", "allocated_days", "used_days", "remaining_days", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "remaining_days", "created_at", "updated_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approved_by_name = serializers.CharField(source="approved_by.display_name", read_only=True, default=None)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "employee", "employee_details", "leave_type", "leave_type_name",
            "start_date", "end_date", "total_days", "reason", "status",
            "approved_by", "approved_by_name", "approved_at", "rejection_reason",
            "created_at", "updated_at"
        ]
        read_only_fields = [
            "id", "total_days", "status", "approved_by", "approved_by_name",
            "approved_at", "rejection_reason", "created_at", "updated_at"
        ]


class LeaveApplySerializer(serializers.Serializer):
    leave_type = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()


class LeaveRejectSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
