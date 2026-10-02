from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BusinessRuleError
from common.permissions import (
    ROLE_TEAM_LEADER,
    IsAdminOrManager,
    IsManagerOrTeamLeader,
    get_employee_scoped_queryset,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import EmployeeFilter
from .models import EmployeeProfile
from .serializers import (
    EmployeeCreateSerializer,
    EmployeeDetailSerializer,
    EmployeeListSerializer,
    EmployeeSelfUpdateSerializer,
    EmployeeUpdateSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List employees", tags=["Employees"]),
    create=extend_schema(summary="Create employee (creates the login account too)", tags=["Employees"]),
    retrieve=extend_schema(summary="Get employee", tags=["Employees"]),
    partial_update=extend_schema(summary="Update employee", tags=["Employees"]),
    destroy=extend_schema(summary="Remove employee profile", tags=["Employees"]),
)
class EmployeeViewSet(EnvelopeModelViewSet):
    queryset = EmployeeProfile.objects.select_related(
        "user", "department", "process", "team", "reporting_manager", "team_leader"
    ).all()
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = EmployeeFilter
    search_fields = ["employee_code", "user__username", "user__first_name", "user__last_name", "user__email"]
    ordering_fields = ["employee_code", "date_of_joining", "created_at"]
    list_message = "Employees retrieved successfully."
    create_message = "Employee created successfully."
    update_message = "Employee updated successfully."
    delete_message = "Employee removed successfully."

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminOrManager()]
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        return get_employee_scoped_queryset(self.request.user, super().get_queryset())

    def get_serializer_class(self):
        if self.action == "create":
            return EmployeeCreateSerializer
        if self.action in ("update", "partial_update"):
            return EmployeeUpdateSerializer
        if self.action == "list":
            return EmployeeListSerializer
        return EmployeeDetailSerializer


class EmployeeMeView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_profile(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if profile is None:
            raise BusinessRuleError("No employee profile is linked to this account.")
        return profile

    @extend_schema(summary="My employee profile", tags=["Employees"])
    def get(self, request):
        return success_response(
            EmployeeDetailSerializer(self._get_profile(request)).data, "Profile retrieved successfully."
        )

    @extend_schema(
        summary="Update my contact details",
        description="Employees cannot modify their own employment information (Section 15).",
        request=EmployeeSelfUpdateSerializer,
        tags=["Employees"],
    )
    def patch(self, request):
        serializer = EmployeeSelfUpdateSerializer(self._get_profile(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, "Profile updated successfully.")