from drf_spectacular.utils import extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.permissions import IsAdminOrManager, get_employee_scoped_queryset, get_team_scoped_queryset
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import ProcessFilter, TeamFilter
from .models import Department, Process, Team
from .serializers import DepartmentSerializer, ProcessSerializer, TeamSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    list=extend_schema(summary="List departments", tags=["Organization"]),
    create=extend_schema(summary="Create department", tags=["Organization"]),
    retrieve=extend_schema(summary="Get department", tags=["Organization"]),
    partial_update=extend_schema(summary="Update department", tags=["Organization"]),
    destroy=extend_schema(summary="Delete department", tags=["Organization"]),
)
class DepartmentViewSet(EnvelopeModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    list_message = "Departments retrieved successfully."
    create_message = "Department created successfully."
    update_message = "Department updated successfully."
    delete_message = "Department deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


@extend_schema_view(
    list=extend_schema(summary="List processes", tags=["Organization"]),
    create=extend_schema(summary="Create process", tags=["Organization"]),
    retrieve=extend_schema(summary="Get process", tags=["Organization"]),
    partial_update=extend_schema(summary="Update process", tags=["Organization"]),
    destroy=extend_schema(summary="Delete process", tags=["Organization"]),
)
class ProcessViewSet(EnvelopeModelViewSet):
    queryset = Process.objects.select_related("department").all()
    serializer_class = ProcessSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = ProcessFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    list_message = "Processes retrieved successfully."
    create_message = "Process created successfully."
    update_message = "Process updated successfully."
    delete_message = "Process deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


@extend_schema_view(
    list=extend_schema(summary="List teams", tags=["Organization"]),
    create=extend_schema(summary="Create team", tags=["Organization"]),
    retrieve=extend_schema(summary="Get team", tags=["Organization"]),
    partial_update=extend_schema(summary="Update team", tags=["Organization"]),
    destroy=extend_schema(summary="Delete team", tags=["Organization"]),
)
class TeamViewSet(EnvelopeModelViewSet):
    queryset = Team.objects.select_related("department", "process", "manager", "team_leader").all()
    serializer_class = TeamSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = TeamFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    list_message = "Teams retrieved successfully."
    create_message = "Team created successfully."
    update_message = "Team updated successfully."
    delete_message = "Team deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve", "employees"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]

    def get_queryset(self):
        return get_team_scoped_queryset(self.request.user, super().get_queryset())

    @action(detail=True, methods=["get"])
    def employees(self, request, pk=None):
        """GET /api/teams/{id}/employees/ — scoped by authorization boundaries."""
        from apps.employees.models import EmployeeProfile
        from apps.employees.serializers import EmployeeListSerializer

        team = self.get_object()
        qs = EmployeeProfile.objects.filter(team=team).select_related("user", "department", "team")
        qs = get_employee_scoped_queryset(request.user, qs)
        page = self.paginate_queryset(qs)
        serializer = EmployeeListSerializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return success_response(serializer.data, "Team employees retrieved successfully.")