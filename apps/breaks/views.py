from django.db.models import Sum
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
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import BreakRecordFilter, BreakTypeFilter
from .models import BreakRecord, BreakStatus, BreakType
from .serializers import (
    BreakRecordSerializer,
    BreakTypeSerializer,
    EndBreakSerializer,
    StartBreakSerializer,
)
from .services import calculate_daily_break_duration, end_break, start_break


@extend_schema_view(
    list=extend_schema(summary="List break types", tags=["Breaks"]),
    create=extend_schema(summary="Create break type", tags=["Breaks"]),
    retrieve=extend_schema(summary="Get break type details", tags=["Breaks"]),
    partial_update=extend_schema(summary="Update break type", tags=["Breaks"]),
    destroy=extend_schema(summary="Delete break type", tags=["Breaks"]),
)
class BreakTypeViewSet(EnvelopeModelViewSet):
    queryset = BreakType.objects.all()
    serializer_class = BreakTypeSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = BreakTypeFilter
    search_fields = ["name"]
    ordering_fields = ["name", "duration_minutes", "created_at"]
    list_message = "Break types retrieved successfully."
    create_message = "Break type created successfully."
    update_message = "Break type updated successfully."
    delete_message = "Break type deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


class StartBreakView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Start a break",
        request=StartBreakSerializer,
        responses={200: BreakRecordSerializer},
        tags=["Breaks"],
    )
    def post(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        serializer = StartBreakSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        break_type_id = serializer.validated_data["break_type_id"]
        start_time = serializer.validated_data.get("start_time")

        record = start_break(profile, break_type_id, start_time=start_time)
        return success_response(BreakRecordSerializer(record).data, "Break started successfully.")


class EndBreakView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="End current active break",
        request=EndBreakSerializer,
        responses={200: BreakRecordSerializer},
        tags=["Breaks"],
    )
    def post(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        serializer = EndBreakSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        end_time = serializer.validated_data.get("end_time")
        record = end_break(profile, end_time=end_time)
        return success_response(BreakRecordSerializer(record).data, "Break ended successfully.")


class MyBreaksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My break history", tags=["Breaks"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = BreakRecord.objects.filter(employee=profile).select_related("break_type").order_by("-start_time")
        filterset = BreakRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(BreakRecordSerializer(records, many=True).data, "My breaks retrieved.")


class MyTodayBreaksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My today's breaks and duration summary", tags=["Breaks"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        today = timezone.localdate()
        records = BreakRecord.objects.filter(employee=profile, start_time__date=today).select_related("break_type").order_by("start_time")
        active_break = records.filter(status=BreakStatus.ACTIVE).first()
        total_duration = calculate_daily_break_duration(profile, today)

        data = {
            "breaks": BreakRecordSerializer(records, many=True).data,
            "active_break": BreakRecordSerializer(active_break).data if active_break else None,
            "total_break_duration_seconds": total_duration,
            "total_break_duration_minutes": round(total_duration / 60, 1),
        }
        return success_response(data, "Today's breaks retrieved successfully.")


@extend_schema_view(
    list=extend_schema(summary="Admin/TL break logs", tags=["Breaks"]),
    retrieve=extend_schema(summary="Get break details", tags=["Breaks"]),
)
class BreakRecordViewSet(EnvelopeModelViewSet):
    queryset = BreakRecord.objects.select_related("employee", "employee__user", "break_type").all()
    serializer_class = BreakRecordSerializer
    http_method_names = ["get"]
    filterset_class = BreakRecordFilter
    search_fields = ["employee__employee_code", "employee__user__username", "break_type__name"]
    ordering_fields = ["start_time", "duration_seconds", "created_at"]
    list_message = "Break records retrieved successfully."

    def get_permissions(self):
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())


class ActiveBreaksView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Employees currently on break", tags=["Breaks"])
    def get(self, request):
        user = request.user
        qs = BreakRecord.objects.filter(status=BreakStatus.ACTIVE).select_related("employee", "employee__user", "break_type")
        qs = get_scoped_queryset(user, qs)

        return success_response(BreakRecordSerializer(qs, many=True).data, "Currently active breaks retrieved.")


class TeamBreaksView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Team break records", tags=["Breaks"])
    def get(self, request):
        user = request.user
        qs = BreakRecord.objects.select_related("employee", "employee__user", "break_type").all()
        qs = get_scoped_queryset(user, qs)

        filterset = BreakRecordFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(BreakRecordSerializer(records, many=True).data, "Team breaks retrieved.")


class DailyBreakSummaryView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Daily break duration summary per employee", tags=["Breaks"])
    def get(self, request):
        date_str = request.GET.get("date")
        date_val = timezone.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.localdate()

        user = request.user
        qs = BreakRecord.objects.filter(start_time__date=date_val, status=BreakStatus.COMPLETED)
        qs = get_scoped_queryset(user, qs)

        summary = (
            qs.values("employee__id", "employee__employee_code", "employee__user__first_name", "employee__user__last_name")
            .annotate(total_seconds=Sum("duration_seconds"))
            .order_by("-total_seconds")
        )

        for row in summary:
            row["total_minutes"] = round(row["total_seconds"] / 60, 1)

        return success_response(list(summary), "Daily break summary retrieved successfully.")
