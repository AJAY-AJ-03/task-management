from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.accounts.serializers import UserBriefSerializer

from .models import EmployeeProfile


class EmployeeListSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ["id", "employee_code", "user", "designation", "department_name", "team_name",
                  "status", "date_of_joining"]
        read_only_fields = fields


class EmployeeDetailSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    process_name = serializers.CharField(source="process.name", read_only=True)
    team_name = serializers.CharField(source="team.name", read_only=True)
    reporting_manager_name = serializers.CharField(
        source="reporting_manager.display_name", read_only=True, default=None
    )
    team_leader_name = serializers.CharField(source="team_leader.display_name", read_only=True, default=None)

    class Meta:
        model = EmployeeProfile
        fields = ["id", "user", "employee_code", "date_of_joining", "designation", "department",
                  "department_name", "process", "process_name", "team", "team_name",
                  "reporting_manager", "reporting_manager_name", "team_leader", "team_leader_name",
                  "phone", "emergency_contact_name", "emergency_contact_phone", "profile_image",
                  "status", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "department_name", "process_name", "team_name",
                             "reporting_manager_name", "team_leader_name", "created_at", "updated_at"]


class EmployeeCreateSerializer(serializers.ModelSerializer):
    """Creates the User and EmployeeProfile together. Restricted to SUPER_ADMIN/MANAGER in views.py."""

    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=Role.choices, write_only=True, default=Role.EMPLOYEE)

    class Meta:
        model = EmployeeProfile
        fields = ["id", "username", "email", "password", "first_name", "last_name", "role",
                  "employee_code", "date_of_joining", "designation", "department", "process",
                  "team", "reporting_manager", "team_leader", "phone", "emergency_contact_name",
                  "emergency_contact_phone", "profile_image", "status"]

    def validate(self, attrs):
        department, process, team = attrs["department"], attrs["process"], attrs["team"]
        if process.department_id != department.id:
            raise serializers.ValidationError({"process": "Process must belong to the selected department."})
        if team.department_id != department.id or team.process_id != process.id:
            raise serializers.ValidationError({"team": "Team must belong to the selected department and process."})

        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user and request.user.role == Role.MANAGER:
            target_role = attrs.get("role", Role.EMPLOYEE)
            if target_role in (Role.SUPER_ADMIN, Role.MANAGER):
                raise serializers.ValidationError({"role": "Managers are not authorized to create Super Admin or Manager accounts."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data.pop("username"),
            email=validated_data.pop("email"),
            password=validated_data.pop("password"),
            first_name=validated_data.pop("first_name"),
            last_name=validated_data.pop("last_name", ""),
            role=validated_data.pop("role"),
            employee_id=validated_data["employee_code"],
        )
        return EmployeeProfile.objects.create(user=user, **validated_data)

    def to_representation(self, instance):
        return EmployeeDetailSerializer(instance, context=self.context).data


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """Admin/manager edits — includes employment fields, which EmployeeSelfUpdateSerializer deliberately omits."""

    class Meta:
        model = EmployeeProfile
        fields = ["employee_code", "date_of_joining", "designation", "department", "process", "team",
                  "reporting_manager", "team_leader", "phone", "emergency_contact_name",
                  "emergency_contact_phone", "profile_image", "status"]

    def validate(self, attrs):
        department = attrs.get("department", self.instance.department)
        process = attrs.get("process", self.instance.process)
        team = attrs.get("team", self.instance.team)
        if process.department_id != department.id:
            raise serializers.ValidationError({"process": "Process must belong to the selected department."})
        if team.department_id != department.id or team.process_id != process.id:
            raise serializers.ValidationError({"team": "Team must belong to the selected department and process."})
        return attrs

    def to_representation(self, instance):
        return EmployeeDetailSerializer(instance, context=self.context).data


class EmployeeSelfUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/employees/me/ — employees may only touch their own contact details."""

    class Meta:
        model = EmployeeProfile
        fields = ["phone", "emergency_contact_name", "emergency_contact_phone", "profile_image"]

    def to_representation(self, instance):
        return EmployeeDetailSerializer(instance, context=self.context).data