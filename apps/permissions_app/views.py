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
    IsManagerOrTeamLeader,
    get_scoped_queryset,
    is_employee_in_actor_scope,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import PermissionRequestFilter
from .models import PermissionRequest, PermissionStatus
from .serializers import (
    PermissionCreateSerializer,
    PermissionRejectSerializer,
    PermissionRequestSerializer,
)


class MyPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My permission requests", tags=["Permissions"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = PermissionRequest.objects.filter(employee=profile).order_by("-date", "-start_time")
        filterset = PermissionRequestFilter(request.GET, queryset=qs)
        requests = filterset.qs if filterset.is_valid() else qs
        return success_response(PermissionRequestSerializer(requests, many=True).data, "My permission requests retrieved.")


@extend_schema_view(
    list=extend_schema(summary="List all permission requests (Admin/TL)", tags=["Permissions"]),
    create=extend_schema(summary="Request permission", request=PermissionCreateSerializer, tags=["Permissions"]),
    retrieve=extend_schema(summary="Get permission request details", tags=["Permissions"]),
)
class PermissionRequestViewSet(EnvelopeModelViewSet):
    queryset = PermissionRequest.objects.select_related("employee", "employee__user", "approved_by").all()
    serializer_class = PermissionRequestSerializer
    http_method_names = ["get", "post"]
    filterset_class = PermissionRequestFilter
    search_fields = ["employee__employee_code", "employee__user__username", "reason"]
    ordering_fields = ["date", "start_time", "created_at"]
    list_message = "Permission requests retrieved successfully."
    create_message = "Permission request submitted successfully."

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

        serializer = PermissionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req = PermissionRequest.objects.create(
            employee=profile,
            date=serializer.validated_data["date"],
            start_time=serializer.validated_data["start_time"],
            end_time=serializer.validated_data["end_time"],
            reason=serializer.validated_data["reason"],
            status=PermissionStatus.PENDING,
        )
        return success_response(PermissionRequestSerializer(req).data, "Permission request submitted successfully.", status_code=201)

    @extend_schema(summary="Approve permission request (Manager/TL)", tags=["Permissions"])
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        perm_req = self.get_object()
        if not is_employee_in_actor_scope(request.user, perm_req.employee):
            raise BusinessRuleError("You are not authorized to approve permission requests for this employee.")

        if perm_req.status != PermissionStatus.PENDING:
            raise BusinessRuleError(f"Cannot approve request with status {perm_req.status}.")

        perm_req.status = PermissionStatus.APPROVED
        perm_req.approved_by = request.user
        perm_req.approved_at = timezone.now()
        perm_req.save()
        return success_response(PermissionRequestSerializer(perm_req).data, "Permission request approved successfully.")

    @extend_schema(summary="Reject permission request (Manager/TL)", request=PermissionRejectSerializer, tags=["Permissions"])
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        perm_req = self.get_object()
        if not is_employee_in_actor_scope(request.user, perm_req.employee):
            raise BusinessRuleError("You are not authorized to reject permission requests for this employee.")

        if perm_req.status != PermissionStatus.PENDING:
            raise BusinessRuleError(f"Cannot reject request with status {perm_req.status}.")

        serializer = PermissionRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        perm_req.status = PermissionStatus.REJECTED
        perm_req.approved_by = request.user
        perm_req.rejection_reason = serializer.validated_data.get("rejection_reason", "")
        perm_req.save()
        return success_response(PermissionRequestSerializer(perm_req).data, "Permission request rejected successfully.")

    @extend_schema(summary="Cancel permission request", tags=["Permissions"])
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        perm_req = self.get_object()
        user = request.user
        if user.role == ROLE_EMPLOYEE:
            profile = getattr(user, "employee_profile", None)
            if not profile or perm_req.employee_id != profile.id:
                raise BusinessRuleError("You are not authorized to cancel this permission request.")

        if perm_req.status in [PermissionStatus.CANCELLED, PermissionStatus.REJECTED]:
            raise BusinessRuleError(f"Permission request is already {perm_req.status.lower()}.")

        perm_req.status = PermissionStatus.CANCELLED
        perm_req.save()
        return success_response(PermissionRequestSerializer(perm_req).data, "Permission request cancelled successfully.")
