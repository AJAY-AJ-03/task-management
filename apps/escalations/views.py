from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import User
from common.exceptions import BusinessRuleError
from common.permissions import (
    ROLE_EMPLOYEE,
    IsManagerOrTeamLeader,
    get_scoped_queryset,
    is_employee_in_actor_scope,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import EscalationFilter
from .models import Escalation, EscalationStatus
from .serializers import (
    EscalationAssignSerializer,
    EscalationSerializer,
    EscalationStatusUpdateSerializer,
)


@extend_schema_view(
    list=extend_schema(summary="List escalations", tags=["Escalations"]),
    create=extend_schema(summary="Create escalation (Employee/TL/Manager)", tags=["Escalations"]),
    retrieve=extend_schema(summary="Get escalation details", tags=["Escalations"]),
    partial_update=extend_schema(summary="Update escalation details", tags=["Escalations"]),
)
class EscalationViewSet(EnvelopeModelViewSet):
    queryset = Escalation.objects.select_related("raised_by", "raised_by__user", "assigned_to", "related_task").all()
    serializer_class = EscalationSerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = EscalationFilter
    search_fields = ["title", "description", "raised_by__employee_code"]
    ordering_fields = ["created_at", "priority", "status"]
    list_message = "Escalations retrieved successfully."
    create_message = "Escalation created successfully."
    update_message = "Escalation updated successfully."

    def get_permissions(self):
        if self.action in ("assign",):
            return [IsManagerOrTeamLeader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset(), employee_field="raised_by")

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")
        serializer.save(raised_by=profile)

    @extend_schema(
        summary="Assign or reassign escalation",
        request=EscalationAssignSerializer,
        responses={200: EscalationSerializer},
        tags=["Escalations"],
    )
    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        escalation = self.get_object()
        serializer = EscalationAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = User.objects.filter(pk=serializer.validated_data["assigned_to"]).first()
        if not target_user:
            raise BusinessRuleError("Target user not found.")

        escalation.assigned_to = target_user
        if escalation.status == EscalationStatus.OPEN:
            escalation.status = EscalationStatus.IN_PROGRESS
        escalation.save()
        return success_response(EscalationSerializer(escalation).data, "Escalation assigned successfully.")

    @extend_schema(
        summary="Update escalation status / resolve / close",
        request=EscalationStatusUpdateSerializer,
        responses={200: EscalationSerializer},
        tags=["Escalations"],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def status_update(self, request, pk=None):
        escalation = self.get_object()
        serializer = EscalationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("resolution_notes", "")

        if request.user.role == ROLE_EMPLOYEE:
            if escalation.raised_by.user_id != request.user.id:
                raise BusinessRuleError("You are not authorized to update this escalation.")

        escalation.status = new_status
        if notes:
            escalation.resolution_notes = notes

        if new_status in (EscalationStatus.RESOLVED, EscalationStatus.CLOSED):
            escalation.resolved_at = timezone.now()

        escalation.save()
        return success_response(EscalationSerializer(escalation).data, "Escalation status updated successfully.")
