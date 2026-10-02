from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id", "employee", "employee_details", "date", "check_in", "check_out",
            "status", "late_minutes", "overtime_minutes", "remarks", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CheckInRequestSerializer(serializers.Serializer):
    check_in = serializers.DateTimeField(required=False, allow_null=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CheckOutRequestSerializer(serializers.Serializer):
    check_out = serializers.DateTimeField(required=False, allow_null=True)


class AttendanceCorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["check_in", "check_out", "status", "late_minutes", "overtime_minutes", "remarks"]
