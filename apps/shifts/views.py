from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BusinessRuleError
from common.permissions import (
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEADER,
    IsAdminOrManager,
    IsManagerOrTeamLeader,
    get_scoped_queryset,
    is_employee_in_actor_scope,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import EmployeeShiftFilter, ShiftFilter
from .models import EmployeeShift, Shift
from .serializers import EmployeeShiftSerializer, ShiftSerializer


@extend_schema_view(
    list=extend_schema(summary="List shifts", tags=["Shifts"]),
    create=extend_schema(summary="Create shift template", tags=["Shifts"]),
    retrieve=extend_schema(summary="Get shift template", tags=["Shifts"]),
    partial_update=extend_schema(summary="Update shift template", tags=["Shifts"]),
    destroy=extend_schema(summary="Delete shift template", tags=["Shifts"]),
)
class ShiftViewSet(EnvelopeModelViewSet):
    queryset = Shift.objects.all()
    serializer_class = ShiftSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = ShiftFilter
    search_fields = ["name"]
    ordering_fields = ["name", "start_time", "created_at"]
    list_message = "Shifts retrieved successfully."
    create_message = "Shift created successfully."
    update_message = "Shift updated successfully."
    delete_message = "Shift deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


@extend_schema_view(
    list=extend_schema(summary="List assigned employee shifts", tags=["Shifts"]),
    create=extend_schema(summary="Assign shift to employee", tags=["Shifts"]),
    retrieve=extend_schema(summary="Get employee shift assignment", tags=["Shifts"]),
    partial_update=extend_schema(summary="Update employee shift assignment", tags=["Shifts"]),
)
class EmployeeShiftViewSet(EnvelopeModelViewSet):
    queryset = EmployeeShift.objects.select_related(
        "employee", "employee__user", "employee__department", "employee__team", "shift", "assigned_by"
    ).all()
    serializer_class = EmployeeShiftSerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = EmployeeShiftFilter
    search_fields = ["employee__employee_code", "employee__user__username", "shift__name"]
    ordering_fields = ["effective_from", "created_at"]
    list_message = "Employee shifts retrieved successfully."
    create_message = "Employee shift assigned successfully."
    update_message = "Employee shift assignment updated successfully."

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAdminOrManager()]
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        emp = serializer.validated_data.get("employee")
        if not is_employee_in_actor_scope(self.request.user, emp):
            raise BusinessRuleError("You are not authorized to assign shifts to this employee.")
        serializer.save(assigned_by=self.request.user)


class MyShiftView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My current active shift", tags=["Shifts"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        today = timezone.localdate()
        shift_assignment = (
            EmployeeShift.objects.filter(employee=profile, effective_from__lte=today)
            .filter(models_q_open_or_future(today))
            .select_related("shift")
            .order_by("-effective_from")
            .first()
        )

        if not shift_assignment:
            return success_response(None, "No active shift assignment found for today.")

        return success_response(
            EmployeeShiftSerializer(shift_assignment).data, "Current shift retrieved successfully."
        )


def models_q_open_or_future(date_val):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=date_val)
