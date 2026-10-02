from rest_framework import serializers

from apps.employees.serializers import EmployeeListSerializer

from .models import EmployeeShift, Shift


class ShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shift
        fields = [
            "id", "name", "start_time", "end_time", "break_duration_minutes",
            "is_overnight", "is_active", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "is_overnight", "created_at", "updated_at"]


class EmployeeShiftSerializer(serializers.ModelSerializer):
    employee_details = EmployeeListSerializer(source="employee", read_only=True)
    shift_details = ShiftSerializer(source="shift", read_only=True)
    assigned_by_name = serializers.CharField(source="assigned_by.display_name", read_only=True, default=None)

    class Meta:
        model = EmployeeShift
        fields = [
            "id", "employee", "employee_details", "shift", "shift_details",
            "effective_from", "effective_to", "assigned_by", "assigned_by_name", "created_at"
        ]
        read_only_fields = ["id", "assigned_by", "assigned_by_name", "created_at"]

    def validate(self, attrs):
        instance = EmployeeShift(**attrs)
        if self.instance:
            instance.pk = self.instance.pk
            instance.employee = attrs.get("employee", self.instance.employee)
            instance.shift = attrs.get("shift", self.instance.shift)
            instance.effective_from = attrs.get("effective_from", self.instance.effective_from)
            instance.effective_to = attrs.get("effective_to", self.instance.effective_to)

        try:
            instance.clean()
        except Exception as e:
            if hasattr(e, "message_dict"):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError(str(e))
        return attrs
