from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer
from common.exceptions import BusinessRuleError
from common.permissions import (
    ROLE_EMPLOYEE,
    IsAdminOrManager,
    IsManagerOrTeamLeader,
    get_scoped_queryset,
    get_task_scoped_queryset,
)
from common.responses import success_response
from common.viewsets import EnvelopeModelViewSet

from .filters import ContactAllocationFilter, ContactFilter
from .models import Contact, ContactAllocation, ContactImport
from .serializers import (
    AllocateContactsSerializer,
    ContactAllocationSerializer,
    ContactAllocationStatusUpdateSerializer,
    ContactImportSerializer,
    ContactReassignSerializer,
    ContactSerializer,
    ExcelUploadSerializer,
)
from .services import (
    allocate_contacts_to_employees,
    parse_and_import_excel,
    reassign_contact_allocation,
    update_contact_allocation_status,
)


class ExcelUploadView(APIView):
    permission_classes = [IsManagerOrTeamLeader]
    parser_classes = [MultiPartParser]

    @extend_schema(
        summary="Upload Excel contacts file (.xlsx)",
        request=ExcelUploadSerializer,
        responses={201: ContactImportSerializer},
        tags=["Contacts & Allocations"],
    )
    def post(self, request):
        serializer = ExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_obj = serializer.validated_data["file"]
        import_log = parse_and_import_excel(file_obj, uploaded_by=request.user)

        return success_response(
            ContactImportSerializer(import_log).data, "Excel contacts imported successfully.", status_code=201
        )


class AllocateContactsView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(
        summary="Allocate selected contacts across selected employees",
        request=AllocateContactsSerializer,
        responses={201: TaskSerializer},
        tags=["Contacts & Allocations"],
    )
    def post(self, request):
        serializer = AllocateContactsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vd = serializer.validated_data
        task = allocate_contacts_to_employees(
            contact_ids=vd["contact_ids"],
            employee_ids=vd["employee_ids"],
            title=vd["title"],
            deadline=vd.get("deadline"),
            notes=vd.get("notes", ""),
            allocated_by=request.user,
        )

        return success_response(
            TaskSerializer(task).data, "Contacts allocated successfully and daily task created.", status_code=201
        )


@extend_schema_view(
    list=extend_schema(summary="List contacts master", tags=["Contacts & Allocations"]),
    retrieve=extend_schema(summary="Get contact details", tags=["Contacts & Allocations"]),
)
class ContactViewSet(EnvelopeModelViewSet):
    queryset = Contact.objects.select_related("contact_import").all()
    serializer_class = ContactSerializer
    http_method_names = ["get"]
    filterset_class = ContactFilter
    search_fields = ["first_name", "last_name", "phone", "email", "company"]
    ordering_fields = ["created_at", "first_name"]
    list_message = "Contacts retrieved successfully."

    def get_permissions(self):
        return [IsManagerOrTeamLeader()]


@extend_schema_view(
    list=extend_schema(summary="List contact allocations", tags=["Contacts & Allocations"]),
    retrieve=extend_schema(summary="Get contact allocation details", tags=["Contacts & Allocations"]),
)
class ContactAllocationViewSet(EnvelopeModelViewSet):
    queryset = ContactAllocation.objects.select_related(
        "task", "contact", "employee", "employee__user", "allocated_by", "updated_by"
    ).all()
    serializer_class = ContactAllocationSerializer
    http_method_names = ["get", "patch"]
    filterset_class = ContactAllocationFilter
    search_fields = ["contact__phone", "contact__first_name", "employee__employee_code"]
    ordering_fields = ["allocated_at", "deadline", "status"]
    list_message = "Contact allocations retrieved successfully."

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        return get_scoped_queryset(self.request.user, super().get_queryset(), employee_field="employee")

    @extend_schema(
        summary="Employee update assigned contact status",
        request=ContactAllocationStatusUpdateSerializer,
        responses={200: ContactAllocationSerializer},
        tags=["Contacts & Allocations"],
    )
    @action(detail=True, methods=["patch"], url_path="status")
    def status_update(self, request, pk=None):
        allocation = self.get_object()

        if request.user.role == ROLE_EMPLOYEE:
            profile = getattr(request.user, "employee_profile", None)
            if not profile or allocation.employee_id != profile.id:
                raise BusinessRuleError("You are not authorized to update this contact allocation.")

        serializer = ContactAllocationStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = update_contact_allocation_status(
            allocation=allocation,
            new_status=serializer.validated_data["status"],
            description=serializer.validated_data.get("description", ""),
            follow_up_date=serializer.validated_data.get("follow_up_date"),
            actor=request.user,
        )

        return success_response(ContactAllocationSerializer(updated).data, "Contact allocation status updated successfully.")

    @extend_schema(
        summary="Reassign incomplete contact allocation (Manager/TL)",
        request=ContactReassignSerializer,
        responses={200: ContactAllocationSerializer},
        tags=["Contacts & Allocations"],
    )
    @action(detail=True, methods=["patch"], url_path="reassign")
    def reassign(self, request, pk=None):
        allocation = self.get_object()
        serializer = ContactReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reassigned = reassign_contact_allocation(
            allocation=allocation,
            new_employee_id=serializer.validated_data["new_employee_id"],
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )

        return success_response(ContactAllocationSerializer(reassigned).data, "Contact allocation reassigned successfully.")


class MyAllocationsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="My active assigned contact allocations", tags=["Contacts & Allocations"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        qs = ContactAllocation.objects.filter(employee=profile, is_active=True).select_related(
            "task", "contact"
        ).order_by("-allocated_at")

        filterset = ContactAllocationFilter(request.GET, queryset=qs)
        allocations = filterset.qs if filterset.is_valid() else qs

        return success_response(
            ContactAllocationSerializer(allocations, many=True).data, "My contact allocations retrieved successfully."
        )


class TaskProgressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Get overall task contact allocation progress metrics", tags=["Contacts & Allocations"])
    def get(self, request, pk=None):
        scoped_tasks = get_task_scoped_queryset(request.user, Task.objects.all())
        task = scoped_tasks.filter(pk=pk).first()
        if not task:
            raise BusinessRuleError("Task not found or access denied.", status_code=404)

        allocations = task.allocations.filter(is_active=True)
        total = allocations.count()

        counts_by_status = {}
        for row in allocations.values("status"):
            st = row["status"]
            counts_by_status[st] = counts_by_status.get(st, 0) + 1

        completed_count = allocations.filter(
            status__in=["COMPLETED", "NO_ANSWER", "CALLBACK", "NOT_INTERESTED", "FAILED"]
        ).count()
        pending_count = allocations.filter(status="PENDING").count()
        in_progress_count = allocations.filter(status="IN_PROGRESS").count()

        progress_pct = round((completed_count / total) * 100, 2) if total > 0 else 0.0

        data = {
            "task_id": task.id,
            "task_title": task.title,
            "overall_status": task.status,
            "total_allocations": total,
            "completed_allocations": completed_count,
            "pending_allocations": pending_count,
            "in_progress_allocations": in_progress_count,
            "completion_percentage": progress_pct,
            "breakdown": counts_by_status,
        }

        return success_response(data, "Task progress metrics retrieved successfully.")
