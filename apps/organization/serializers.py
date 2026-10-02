from rest_framework import serializers

from .models import Department, Process, Team


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProcessSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Process
        fields = ["id", "department", "department_name", "name", "description", "is_active",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "department_name", "created_at", "updated_at"]


class TeamSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)
    manager_name = serializers.CharField(source="manager.display_name", read_only=True, default=None)
    team_leader_name = serializers.CharField(source="team_leader.display_name", read_only=True, default=None)

    class Meta:
        model = Team
        fields = ["id", "name", "department", "department_name", "process", "process_name",
                  "manager", "manager_name", "team_leader", "team_leader_name", "description",
                  "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "department_name", "process_name", "manager_name",
                             "team_leader_name", "created_at", "updated_at"]

    def validate(self, attrs):
        department = attrs.get("department", getattr(self.instance, "department", None))
        process = attrs.get("process", getattr(self.instance, "process", None))
        if department and process and process.department_id != department.id:
            raise serializers.ValidationError({"process": "Process must belong to the selected department."})
        manager = attrs.get("manager", getattr(self.instance, "manager", None))
        if manager and manager.role not in ("SUPER_ADMIN", "MANAGER"):
            raise serializers.ValidationError({"manager": "Assigned manager must have the MANAGER role."})
        team_leader = attrs.get("team_leader", getattr(self.instance, "team_leader", None))
        if team_leader and team_leader.role not in ("SUPER_ADMIN", "TEAM_LEADER"):
            raise serializers.ValidationError({"team_leader": "Assigned team leader must have the TEAM_LEADER role."})
        return attrs