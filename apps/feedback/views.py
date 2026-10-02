from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.exceptions import BusinessRuleError
from common.permissions import IsManagerOrTeamLeader, get_scoped_queryset
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import FeedbackFilter
from .models import Feedback, FeedbackStatus
from .serializers import FeedbackRespondSerializer, FeedbackSerializer


@extend_schema_view(
    list=extend_schema(summary="List feedback submissions", tags=["Feedback"]),
    create=extend_schema(summary="Submit feedback (Employee/All)", tags=["Feedback"]),
    retrieve=extend_schema(summary="Get feedback details", tags=["Feedback"]),
    partial_update=extend_schema(summary="Update feedback", tags=["Feedback"]),
)
class FeedbackViewSet(EnvelopeModelViewSet):
    queryset = Feedback.objects.select_related("employee", "employee__user", "reviewed_by").all()
    serializer_class = FeedbackSerializer
    http_method_names = ["get", "post", "patch"]
    filterset_class = FeedbackFilter
    search_fields = ["subject", "description", "category", "employee__employee_code"]
    ordering_fields = ["created_at", "status", "rating"]
    list_message = "Feedback entries retrieved successfully."
    create_message = "Feedback submitted successfully."
    update_message = "Feedback updated successfully."

    def get_permissions(self):
        if self.action in ("respond",):
            return [IsManagerOrTeamLeader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset(), employee_field="employee")

    def perform_create(self, serializer):
        profile = getattr(self.request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")
        serializer.save(employee=profile, status=FeedbackStatus.SUBMITTED)

    @extend_schema(
        summary="Respond to employee feedback (Manager/TL/Admin)",
        request=FeedbackRespondSerializer,
        responses={200: FeedbackSerializer},
        tags=["Feedback"],
    )
    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        fb = self.get_object()
        serializer = FeedbackRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fb.status = serializer.validated_data["status"]
        fb.response = serializer.validated_data["response"]
        fb.reviewed_by = request.user
        fb.reviewed_at = timezone.now()
        fb.save()

        return success_response(FeedbackSerializer(fb).data, "Feedback response saved successfully.")
