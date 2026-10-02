from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
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

from .filters import AttendanceFilter
from .models import Attendance
from .serializers import (
    AttendanceCorrectionSerializer,
    AttendanceSerializer,
    CheckInRequestSerializer,
    CheckOutRequestSerializer,
)
from .services import check_in_employee, check_out_employee


class CheckInView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Employee check-in",
        request=CheckInRequestSerializer,
        responses={200: AttendanceSerializer},
        tags=["Attendance"],
    )
    def post(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        serializer = CheckInRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check_in_time = serializer.validated_data.get("check_in")
        remarks = serializer.validated_data.get("remarks", "")

        record = check_in_employee(profile, check_in_dt=check_in_time, remarks=remarks)
        return success_response(AttendanceSerializer(record).data, "Attendance checked in successfully.")


class CheckOutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Employee check-out",
        request=CheckOutRequestSerializer,
        responses={200: AttendanceSerializer},
        tags=["Attendance"],
    )
    def post(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        serializer = CheckOutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check_out_time = serializer.validated_data.get("check_out")

        record = check_out_employee(profile, check_out_dt=check_out_time)
        return success_response(AttendanceSerializer(record).data, "Attendance checked out successfully.")


class MyAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My attendance history", tags=["Attendance"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = Attendance.objects.filter(employee=profile).order_by("-date")
        filterset = AttendanceFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(AttendanceSerializer(records, many=True).data, "My attendance retrieved.")


class MyTodayAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My today attendance record", tags=["Attendance"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        today = timezone.localdate()
        record = Attendance.objects.filter(employee=profile, date=today).first()
        data = AttendanceSerializer(record).data if record else None
        return success_response(data, "Today's attendance record retrieved.")


@extend_schema_view(
    list=extend_schema(summary="Admin/TL attendance list", tags=["Attendance"]),
    retrieve=extend_schema(summary="Get attendance details", tags=["Attendance"]),
    partial_update=extend_schema(summary="Attendance correction by authorized role", tags=["Attendance"]),
)
class AttendanceViewSet(EnvelopeModelViewSet):
    queryset = Attendance.objects.select_related("employee", "employee__user", "employee__department", "employee__team").all()
    serializer_class = AttendanceSerializer
    http_method_names = ["get", "patch"]
    filterset_class = AttendanceFilter
    search_fields = ["employee__employee_code", "employee__user__username", "remarks"]
    ordering_fields = ["date", "check_in", "created_at"]
    list_message = "Attendance records retrieved successfully."
    update_message = "Attendance record corrected successfully."

    def get_permissions(self):
        if self.action in ("partial_update", "update"):
            return [IsAdminOrManager()]
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())

    def get_serializer_class(self):
        if self.action in ("partial_update", "update"):
            return AttendanceCorrectionSerializer
        return AttendanceSerializer


class TeamAttendanceView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Team attendance list", tags=["Attendance"])
    def get(self, request):
        user = request.user
        qs = Attendance.objects.select_related("employee", "employee__user", "employee__team").all()
        qs = get_scoped_queryset(user, qs)

        filterset = AttendanceFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(AttendanceSerializer(records, many=True).data, "Team attendance retrieved.")


class MonthlyAttendanceView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Monthly attendance breakdown", tags=["Attendance"])
    def get(self, request):
        user = request.user
        qs = Attendance.objects.select_related("employee", "employee__user").all()
        qs = get_scoped_queryset(user, qs)

        filterset = AttendanceFilter(request.GET, queryset=qs)
        records = filterset.qs if filterset.is_valid() else qs
        return success_response(AttendanceSerializer(records, many=True).data, "Monthly attendance retrieved.")
