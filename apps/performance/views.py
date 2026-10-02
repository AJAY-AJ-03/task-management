from django.db.models import Avg, Sum
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

from .filters import EmployeeKPIFilter, KPIFilter, PerformanceRecordFilter
from .models import KPI, EmployeeKPI, PerformanceRecord
from .serializers import EmployeeKPISerializer, KPISerializer, PerformanceRecordSerializer
from .services import record_daily_performance


@extend_schema_view(
    list=extend_schema(summary="List KPI master templates", tags=["Performance"]),
    create=extend_schema(summary="Create KPI master template", tags=["Performance"]),
    retrieve=extend_schema(summary="Get KPI details", tags=["Performance"]),
    partial_update=extend_schema(summary="Update KPI master template", tags=["Performance"]),
    destroy=extend_schema(summary="Delete KPI master template", tags=["Performance"]),
)
class KPIViewSet(EnvelopeModelViewSet):
    queryset = KPI.objects.all()
    serializer_class = KPISerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = KPIFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    list_message = "KPIs retrieved successfully."
    create_message = "KPI created successfully."
    update_message = "KPI updated successfully."
    delete_message = "KPI deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


@extend_schema_view(
    list=extend_schema(summary="List assigned employee KPI targets", tags=["Performance"]),
    create=extend_schema(summary="Assign KPI target to employee", tags=["Performance"]),
    retrieve=extend_schema(summary="Get employee KPI target details", tags=["Performance"]),
    partial_update=extend_schema(summary="Update employee KPI target", tags=["Performance"]),
)
class EmployeeKPIViewSet(EnvelopeModelViewSet):
    queryset = EmployeeKPI.objects.select_related("employee", "employee__user", "kpi").all()
    serializer_class = EmployeeKPISerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = EmployeeKPIFilter
    search_fields = ["employee__employee_code", "employee__user__username", "kpi__name"]
    ordering_fields = ["effective_from", "created_at"]
    list_message = "Employee KPI targets retrieved successfully."
    create_message = "Employee KPI target assigned successfully."
    update_message = "Employee KPI target updated successfully."

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAdminOrManager()]
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        emp = serializer.validated_data.get("employee")
        if not is_employee_in_actor_scope(self.request.user, emp):
            raise BusinessRuleError("You are not authorized to assign KPI target to this employee.")
        serializer.save()


class MyKPIsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My assigned KPI targets", tags=["Performance"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        today = timezone.localdate()
        targets = (
            EmployeeKPI.objects.filter(employee=profile, effective_from__lte=today)
            .filter(models_q_open_or_future(today))
            .select_related("kpi")
        )
        return success_response(EmployeeKPISerializer(targets, many=True).data, "My KPI targets retrieved.")


@extend_schema_view(
    list=extend_schema(summary="List performance records", tags=["Performance"]),
    create=extend_schema(summary="Create performance record", tags=["Performance"]),
    retrieve=extend_schema(summary="Get performance record details", tags=["Performance"]),
    partial_update=extend_schema(summary="Update performance record", tags=["Performance"]),
)
class PerformanceRecordViewSet(EnvelopeModelViewSet):
    queryset = PerformanceRecord.objects.select_related("employee", "employee__user", "kpi", "created_by").all()
    serializer_class = PerformanceRecordSerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = PerformanceRecordFilter
    search_fields = ["employee__employee_code", "employee__user__username", "kpi__name", "remarks"]
    ordering_fields = ["date", "achievement_percentage", "created_at"]
    list_message = "Performance records retrieved successfully."
    create_message = "Performance record saved successfully."
    update_message = "Performance record updated successfully."

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsManagerOrTeamLeader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        emp = serializer.validated_data.get("employee")
        if not is_employee_in_actor_scope(self.request.user, emp):
            raise BusinessRuleError("You are not authorized to create performance records for this employee.")
        serializer.save(created_by=self.request.user)


class MyPerformanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My performance history", tags=["Performance"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = PerformanceRecord.objects.filter(employee=profile).select_related("kpi").order_by("-date")
        filterset = PerformanceRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(PerformanceRecordSerializer(records, many=True).data, "My performance history retrieved.")


class DailyPerformanceReportView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Daily performance summary", tags=["Performance"])
    def get(self, request):
        date_str = request.GET.get("date")
        date_val = timezone.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()

        user = request.user
        qs = PerformanceRecord.objects.filter(date=date_val).select_related("employee", "employee__user", "kpi")
        qs = get_scoped_queryset(user, qs)

        filterset = PerformanceRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(PerformanceRecordSerializer(records, many=True).data, "Daily performance summary retrieved.")


class TeamPerformanceReportView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Team average performance summary", tags=["Performance"])
    def get(self, request):
        user = request.user
        qs = PerformanceRecord.objects.select_related("employee", "employee__team", "kpi").all()
        qs = get_scoped_queryset(user, qs)

        filterset = PerformanceRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs

        summary = (
            records.values("employee__team__id", "employee__team__name", "kpi__name")
            .annotate(avg_achievement=Avg("achievement_percentage"))
            .order_by("employee__team__name")
        )
        return success_response(list(summary), "Team performance summary retrieved successfully.")


class MonthlyPerformanceReportView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Monthly performance summary", tags=["Performance"])
    def get(self, request):
        user = request.user
        qs = PerformanceRecord.objects.select_related("employee", "employee__user", "kpi").all()
        qs = get_scoped_queryset(user, qs)

        filterset = PerformanceRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(PerformanceRecordSerializer(records, many=True).data, "Monthly performance summary retrieved.")


def models_q_open_or_future(date_val):
    from django.db.models import Q
    return Q(effective_to__isnull=True) | Q(effective_to__gte=date_val)
