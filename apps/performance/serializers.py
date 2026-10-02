from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import KPI, EmployeeKPI, PerformanceRecord


class KPISerializer(serializers.ModelSerializer):
    class Meta:
        model = KPI
        fields = ["id", "name", "description", "unit", "target_type", "default_target", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmployeeKPISerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    kpi_name = serializers.CharField(source="kpi.name", read_only=True)

    class Meta:
        model = EmployeeKPI
        fields = ["id", "employee", "employee_details", "kpi", "kpi_name", "target", "effective_from", "effective_to", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PerformanceRecordSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    kpi_name = serializers.CharField(source="kpi.name", read_only=True)
    unit = serializers.CharField(source="kpi.unit", read_only=True)
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True, default=None)

    class Meta:
        model = PerformanceRecord
        fields = [
            "id", "employee", "employee_details", "kpi", "kpi_name", "unit", "date",
            "target_value", "actual_value", "achievement_percentage", "remarks",
            "created_by", "created_by_name", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "achievement_percentage", "created_by", "created_by_name", "created_at", "updated_at"]
