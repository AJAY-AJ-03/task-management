from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BusinessRuleError
from common.permissions import (
    ROLE_EMPLOYEE,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEADER,
    IsAdminOrManager,
    IsManagerOrTeamLeader,
    get_scoped_queryset,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import LeaveBalanceFilter, LeaveRequestFilter, LeaveTypeFilter
from .models import LeaveBalance, LeaveRequest, LeaveType
from .serializers import (
    LeaveApplySerializer,
    LeaveBalanceSerializer,
    LeaveRejectSerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
)
from .services import apply_leave, approve_leave, cancel_leave, reject_leave


@extend_schema_view(
    list=extend_schema(summary="List leave types", tags=["Leave"]),
    create=extend_schema(summary="Create leave type", tags=["Leave"]),
    retrieve=extend_schema(summary="Get leave type details", tags=["Leave"]),
    partial_update=extend_schema(summary="Update leave type", tags=["Leave"]),
    destroy=extend_schema(summary="Delete leave type", tags=["Leave"]),
)
class LeaveTypeViewSet(EnvelopeModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = LeaveTypeFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "default_days", "created_at"]
    list_message = "Leave types retrieved successfully."
    create_message = "Leave type created successfully."
    update_message = "Leave type updated successfully."
    delete_message = "Leave type deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsAdminOrManager()]


class MyLeaveBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My leave balances for the current year", tags=["Leave"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        year = timezone.localdate().year
        balances = LeaveBalance.objects.filter(employee=profile, year=year).select_related("leave_type")
        return success_response(LeaveBalanceSerializer(balances, many=True).data, "My leave balances retrieved.")


class MyLeaveRequestsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My leave request history", tags=["Leave"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = LeaveRequest.objects.filter(employee=profile).select_related("leave_type", "approved_by").order_by("-start_date")
        filterset = LeaveRequestFilter(request.GET, queryset=qs)
        requests = filterset.qs if filterset.is_valid() else qs
        return success_response(LeaveRequestSerializer(requests, many=True).data, "My leave requests retrieved.")


@extend_schema_view(
    list=extend_schema(summary="List all leave requests (Admin/TL)", tags=["Leave"]),
    create=extend_schema(summary="Apply for leave", request=LeaveApplySerializer, tags=["Leave"]),
    retrieve=extend_schema(summary="Get leave request details", tags=["Leave"]),
)
class LeaveRequestViewSet(EnvelopeModelViewSet):
    queryset = LeaveRequest.objects.select_related("employee", "employee__user", "leave_type", "approved_by").all()
    serializer_class = LeaveRequestSerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = LeaveRequestFilter
    search_fields = ["employee__employee_code", "employee__user__username", "reason"]
    ordering_fields = ["start_date", "created_at"]
    list_message = "Leave requests retrieved successfully."
    create_message = "Leave request submitted successfully."

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [IsManagerOrTeamLeader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset())

    def create(self, request, *args, **kwargs):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        serializer = LeaveApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = apply_leave(
            employee=profile,
            leave_type_id=serializer.validated_data["leave_type"],
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
            reason=serializer.validated_data["reason"],
        )
        return success_response(LeaveRequestSerializer(req).data, "Leave request submitted successfully.", status_code=201)

    @extend_schema(summary="Approve leave request (Manager/TL)", tags=["Leave"])
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        leave_req = self.get_object()
        approved = approve_leave(leave_req, request.user)
        return success_response(LeaveRequestSerializer(approved).data, "Leave request approved successfully.")

    @extend_schema(summary="Reject leave request (Manager/TL)", request=LeaveRejectSerializer, tags=["Leave"])
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        leave_req = self.get_object()
        serializer = LeaveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get("rejection_reason", "")
        rejected = reject_leave(leave_req, request.user, rejection_reason=reason)
        return success_response(LeaveRequestSerializer(rejected).data, "Leave request rejected successfully.")

    @extend_schema(summary="Cancel leave request", tags=["Leave"])
    @action(detail=True, methods=["patch"], url_path="cancel")
    def cancel(self, request, pk=None):
        leave_req = self.get_object()
        user = request.user
        if user.role == ROLE_EMPLOYEE:
            profile = getattr(user, "employee_profile", None)
            if not profile or leave_req.employee_id != profile.id:
                raise BusinessRuleError("You are not authorized to cancel this leave request.")

        cancelled = cancel_leave(leave_req)
        return success_response(LeaveRequestSerializer(cancelled).data, "Leave request cancelled successfully.")
