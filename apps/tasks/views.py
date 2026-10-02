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
    get_task_scoped_queryset,
    is_employee_in_actor_scope,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import TaskFilter
from .models import Task, TaskActivity
from .serializers import TaskActivitySerializer, TaskAssignSerializer, TaskSerializer, TaskStatusUpdateSerializer
from .services import reassign_task, update_task_status


@extend_schema_view(
    list=extend_schema(summary="List tasks", tags=["Tasks"]),
    create=extend_schema(summary="Create task (Manager/TL)", tags=["Tasks"]),
    retrieve=extend_schema(summary="Get task details", tags=["Tasks"]),
    partial_update=extend_schema(summary="Update task", tags=["Tasks"]),
    destroy=extend_schema(summary="Delete task", tags=["Tasks"]),
)
class TaskViewSet(EnvelopeModelViewSet):
    queryset = Task.objects.select_related(
        "assigned_to", "assigned_to__user", "assigned_by", "team"
    ).all()
    serializer_class = TaskSerializer
    http_method_names = ["get", "post", "patch", "delete"]
    filterset_class = TaskFilter
    search_fields = ["title", "description", "assigned_to__employee_code", "assigned_to__user__username"]
    ordering_fields = ["due_date", "priority", "created_at"]
    list_message = "Tasks retrieved successfully."
    create_message = "Task created successfully."
    update_message = "Task updated successfully."
    delete_message = "Task deleted successfully."

    def get_permissions(self):
        if self.action in ("create", "destroy", "assign"):
            return [IsManagerOrTeamLeader()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_task_scoped_queryset(self.request.user, super().get_queryset())

    def perform_create(self, serializer):
        assigned_to = serializer.validated_data.get("assigned_to")
        if assigned_to and not is_employee_in_actor_scope(self.request.user, assigned_to):
            raise BusinessRuleError("You are not authorized to assign tasks to this employee.")
        serializer.save(assigned_by=self.request.user)

    @extend_schema(
        summary="Update task status (Employee or Manager/TL)",
        request=TaskStatusUpdateSerializer,
        responses={200: TaskSerializer},
        tags=["Tasks"],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def status(self, request, pk=None):
        task = self.get_object()
        user = request.user

        # Employee check: can only update task assigned to them
        if user.role == ROLE_EMPLOYEE:
            profile = getattr(user, "employee_profile", None)
            if not profile or task.assigned_to_id != profile.id:
                raise BusinessRuleError("You are not authorized to update this task.")

        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_task = update_task_status(task, serializer.validated_data["status"], actor=request.user)
        return success_response(TaskSerializer(updated_task).data, "Task status updated successfully.")

    @extend_schema(
        summary="Assign or reassign task to an employee (Manager/TL)",
        request=TaskAssignSerializer,
        responses={200: TaskSerializer},
        tags=["Tasks"],
    )
    @action(detail=True, methods=["patch"], url_path="assign")
    def assign(self, request, pk=None):
        task = self.get_object()
        serializer = TaskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reassigned = reassign_task(task, serializer.validated_data["assigned_to"], request.user)
        return success_response(TaskSerializer(reassigned).data, "Task reassigned successfully.")


class MyTasksView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My assigned tasks", tags=["Tasks"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = Task.objects.filter(assigned_to=profile).select_related("assigned_by", "team").order_by("-created_at")
        filterset = TaskFilter(request.GET, queryset=qs)
        tasks = filterset.qs if filterset.is_valid() else qs
        return success_response(TaskSerializer(tasks, many=True).data, "My tasks retrieved successfully.")


class TeamTasksView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Team tasks list", tags=["Tasks"])
    def get(self, request):
        user = request.user
        qs = Task.objects.select_related("assigned_to", "assigned_to__user", "team").all()
        qs = get_task_scoped_queryset(user, qs)

        filterset = TaskFilter(request.GET, queryset=qs)
        tasks = filterset.qs if filterset.is_valid() else qs
        return success_response(TaskSerializer(tasks, many=True).data, "Team tasks retrieved successfully.")


@extend_schema_view(
    list=extend_schema(summary="List task activity history", tags=["Tasks"]),
    retrieve=extend_schema(summary="Get task activity record", tags=["Tasks"]),
)
class TaskActivityViewSet(EnvelopeModelViewSet):
    queryset = TaskActivity.objects.select_related("task", "actor").all()
    serializer_class = TaskActivitySerializer
    http_method_names = ["get"]
    ordering_fields = ["created_at", "action"]
    list_message = "Task activities retrieved successfully."

    def get_queryset(self):
        user = self.request.user
        scoped_tasks = get_task_scoped_queryset(user, Task.objects.all())
        return super().get_queryset().filter(task__in=scoped_tasks)
