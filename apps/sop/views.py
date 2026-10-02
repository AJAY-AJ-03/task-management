from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.permissions import IsAuthenticated

from common.permissions import (
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEADER,
    IsAdminOrManager,
    IsManagerOrTeamLeader,
)
from common.viewsets import EnvelopeModelViewSet

from .filters import SOPFilter
from .models import SOP, SOPStatus
from .serializers import SOPSerializer


@extend_schema_view(
    list=extend_schema(summary="List Knowledge Base SOPs", tags=["Knowledge Base"]),
    create=extend_schema(summary="Create SOP (Manager/TL/Admin)", tags=["Knowledge Base"]),
    retrieve=extend_schema(summary="Get SOP details", tags=["Knowledge Base"]),
    partial_update=extend_schema(summary="Update SOP", tags=["Knowledge Base"]),
    destroy=extend_schema(summary="Delete SOP", tags=["Knowledge Base"]),
)
class SOPViewSet(EnvelopeModelViewSet):
    queryset = SOP.objects.select_related("department", "process", "team", "created_by", "updated_by").all()
    serializer_class = SOPSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = SOPFilter
    search_fields = ["title", "content", "category"]
    ordering_fields = ["updated_at", "title", "created_at"]
    list_message = "SOPs retrieved successfully."
    create_message = "SOP created successfully."
    update_message = "SOP updated successfully."
    delete_message = "SOP deleted successfully."

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAuthenticated()]
        return [IsManagerOrTeamLeader()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user or not user.is_authenticated:
            return qs.none()

        if user.role == ROLE_SUPER_ADMIN:
            return qs

        if user.role == ROLE_EMPLOYEE:
            profile = getattr(user, "employee_profile", None)
            if not profile:
                return qs.none()
            # Only published SOPs relevant to employee's scope or global
            dept_q = Q(department__isnull=True) | Q(department=profile.department_id)
            proc_q = Q(process__isnull=True) | Q(process=profile.process_id)
            team_q = Q(team__isnull=True) | Q(team=profile.team_id)
            return qs.filter(status=SOPStatus.PUBLISHED).filter(dept_q & proc_q & team_q)

        if user.role == ROLE_TEAM_LEADER:
            # TL can see all published SOPs or SOPs linked to led teams / created by self
            profile = getattr(user, "employee_profile", None)
            team_id = profile.team_id if profile else None
            return qs.filter(
                Q(status=SOPStatus.PUBLISHED)
                | Q(team__team_leader=user)
                | Q(team_id=team_id)
                | Q(created_by=user)
            ).distinct()

        if user.role == ROLE_MANAGER:
            return qs.filter(
                Q(status=SOPStatus.PUBLISHED)
                | Q(team__manager=user)
                | Q(department__teams__manager=user)
                | Q(created_by=user)
            ).distinct()

        return qs.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
