from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from apps.attendance.models import Attendance
from apps.breaks.models import BreakRecord
from apps.contacts.models import ContactAllocation
from apps.employees.models import EmployeeProfile
from apps.leave.models import LeaveRequest
from apps.performance.models import PerformanceRecord
from apps.tasks.models import Task
from common.permissions import IsManagerOrTeamLeader, get_scoped_queryset, get_task_scoped_queryset
from common.responses import success_response

from .exporters import export_response


def apply_report_filters(qs, request_get, is_task=False):
    team_id = request_get.get("team")
    employee_id = request_get.get("employee")
    department_id = request_get.get("department")
    process_id = request_get.get("process")
    manager_id = request_get.get("manager")

    if is_task:
        if team_id:
            qs = qs.filter(team_id=team_id)
        if employee_id:
            qs = qs.filter(assigned_to_id=employee_id)
        if department_id:
            qs = qs.filter(assigned_to__department_id=department_id)
        if process_id:
            qs = qs.filter(assigned_to__process_id=process_id)
        if manager_id:
            qs = qs.filter(assigned_to__reporting_manager_id=manager_id)
    else:
        if team_id:
            qs = qs.filter(employee__team_id=team_id)
        if employee_id:
            qs = qs.filter(employee_id=employee_id)
        if department_id:
            qs = qs.filter(employee__department_id=department_id)
        if process_id:
            qs = qs.filter(employee__process_id=process_id)
        if manager_id:
            qs = qs.filter(employee__reporting_manager_id=manager_id)

    return qs


class BaseReportView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    def perform_content_negotiation(self, request, force=False):
        # Prevent DRF content negotiation from raising 404/406 on custom format params (e.g. ?format=csv or ?format=excel)
        return (JSONRenderer(), JSONRenderer.media_type)


class AttendanceReportView(BaseReportView):
    @extend_schema(summary="Attendance report export", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        qs = Attendance.objects.select_related("employee", "employee__user", "employee__department", "employee__team").all()
        qs = get_scoped_queryset(request.user, qs)
        qs = apply_report_filters(qs, request.GET, is_task=False)

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        rows = []
        for a in qs:
            rows.append({
                "Employee Code": a.employee.employee_code,
                "Employee Name": a.employee.user.display_name,
                "Department": a.employee.department.name if a.employee.department else "",
                "Team": a.employee.team.name if a.employee.team else "",
                "Date": str(a.date),
                "Check In": a.check_in.strftime("%Y-%m-%d %H:%M") if a.check_in else "",
                "Check Out": a.check_out.strftime("%Y-%m-%d %H:%M") if a.check_out else "",
                "Status": a.status,
                "Late Minutes": a.late_minutes,
                "Overtime Minutes": a.overtime_minutes,
            })

        headers = ["Employee Code", "Employee Name", "Department", "Team", "Date", "Check In", "Check Out", "Status", "Late Minutes", "Overtime Minutes"]
        resp = export_response(rows, headers, "attendance_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Attendance report generated.")


class ProductivityReportView(BaseReportView):
    @extend_schema(summary="Productivity report export", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        qs = PerformanceRecord.objects.select_related("employee", "employee__user", "kpi").all()
        qs = get_scoped_queryset(request.user, qs)
        qs = apply_report_filters(qs, request.GET, is_task=False)

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        rows = []
        for p in qs:
            rows.append({
                "Employee Code": p.employee.employee_code,
                "Employee Name": p.employee.user.display_name,
                "KPI Name": p.kpi.name,
                "Date": str(p.date),
                "Target Value": str(p.target_value),
                "Actual Value": str(p.actual_value),
                "Achievement %": str(p.achievement_percentage),
            })

        headers = ["Employee Code", "Employee Name", "KPI Name", "Date", "Target Value", "Actual Value", "Achievement %"]
        resp = export_response(rows, headers, "productivity_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Productivity report generated.")


class PerformanceReportView(BaseReportView):
    @extend_schema(summary="Performance report export", tags=["Reports"])
    def get(self, request):
        return ProductivityReportView().get(request)


class BreaksReportView(BaseReportView):
    @extend_schema(summary="Breaks report export", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        qs = BreakRecord.objects.select_related("employee", "employee__user", "break_type").all()
        qs = get_scoped_queryset(request.user, qs)
        qs = apply_report_filters(qs, request.GET, is_task=False)

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            qs = qs.filter(start_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(start_time__date__lte=end_date)

        rows = []
        for b in qs:
            rows.append({
                "Employee Code": b.employee.employee_code,
                "Employee Name": b.employee.user.display_name,
                "Break Type": b.break_type.name,
                "Start Time": b.start_time.strftime("%Y-%m-%d %H:%M:%S") if b.start_time else "",
                "End Time": b.end_time.strftime("%Y-%m-%d %H:%M:%S") if b.end_time else "",
                "Duration (Minutes)": round(b.duration_seconds / 60, 1),
                "Status": b.status,
            })

        headers = ["Employee Code", "Employee Name", "Break Type", "Start Time", "End Time", "Duration (Minutes)", "Status"]
        resp = export_response(rows, headers, "breaks_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Breaks report generated.")


class TasksReportView(BaseReportView):
    @extend_schema(summary="Tasks report export", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        qs = Task.objects.select_related("assigned_to", "assigned_to__user", "team").all()
        qs = get_task_scoped_queryset(request.user, qs)
        qs = apply_report_filters(qs, request.GET, is_task=True)

        rows = []
        for t in qs:
            rows.append({
                "Task Title": t.title,
                "Assigned To Code": t.assigned_to.employee_code,
                "Assigned To Name": t.assigned_to.user.display_name,
                "Team": t.team.name if t.team else "",
                "Priority": t.priority,
                "Status": t.status,
                "Due Date": str(t.due_date) if t.due_date else "",
                "Completed At": t.completed_at.strftime("%Y-%m-%d %H:%M") if t.completed_at else "",
            })

        headers = ["Task Title", "Assigned To Code", "Assigned To Name", "Team", "Priority", "Status", "Due Date", "Completed At"]
        resp = export_response(rows, headers, "tasks_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Tasks report generated.")


class LeaveReportView(BaseReportView):
    @extend_schema(summary="Leave report export", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        qs = LeaveRequest.objects.select_related("employee", "employee__user", "leave_type").all()
        qs = get_scoped_queryset(request.user, qs)
        qs = apply_report_filters(qs, request.GET, is_task=False)

        rows = []
        for l in qs:
            rows.append({
                "Employee Code": l.employee.employee_code,
                "Employee Name": l.employee.user.display_name,
                "Leave Type": l.leave_type.name,
                "Start Date": str(l.start_date),
                "End Date": str(l.end_date),
                "Total Days": str(l.total_days),
                "Reason": l.reason,
                "Status": l.status,
            })

        headers = ["Employee Code", "Employee Name", "Leave Type", "Start Date", "End Date", "Total Days", "Reason", "Status"]
        resp = export_response(rows, headers, "leave_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Leave report generated.")


class EmployeeProductivityReportView(BaseReportView):
    @extend_schema(summary="Employee productivity report", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        emp_qs = get_scoped_queryset(request.user, EmployeeProfile.objects.select_related("user", "team", "department", "process").all())

        if request.GET.get("employee"):
            emp_qs = emp_qs.filter(id=request.GET.get("employee"))
        if request.GET.get("team"):
            emp_qs = emp_qs.filter(team_id=request.GET.get("team"))
        if request.GET.get("department"):
            emp_qs = emp_qs.filter(department_id=request.GET.get("department"))
        if request.GET.get("process"):
            emp_qs = emp_qs.filter(process_id=request.GET.get("process"))

        allocations = ContactAllocation.objects.filter(employee__in=emp_qs)

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            allocations = allocations.filter(allocated_at__date__gte=start_date)
        if end_date:
            allocations = allocations.filter(allocated_at__date__lte=end_date)
        if request.GET.get("task"):
            allocations = allocations.filter(task_id=request.GET.get("task"))
        if request.GET.get("status"):
            allocations = allocations.filter(status=request.GET.get("status"))

        stats = {}
        for emp in emp_qs:
            stats[emp.id] = {
                "employee_code": emp.employee_code,
                "employee_name": emp.user.display_name,
                "team": emp.team.name if emp.team else "",
                "assigned": 0,
                "completed": 0,
                "pending": 0,
                "outcomes": {
                    "PENDING": 0,
                    "IN_PROGRESS": 0,
                    "COMPLETED": 0,
                    "NO_ANSWER": 0,
                    "CALLBACK": 0,
                    "NOT_INTERESTED": 0,
                    "FAILED": 0,
                },
            }

        for alloc in allocations:
            if alloc.employee_id in stats:
                st = stats[alloc.employee_id]
                st["assigned"] += 1
                if alloc.status == "COMPLETED":
                    st["completed"] += 1
                elif alloc.status in ["PENDING", "IN_PROGRESS"]:
                    st["pending"] += 1
                if alloc.status in st["outcomes"]:
                    st["outcomes"][alloc.status] += 1
                else:
                    st["outcomes"][alloc.status] = 1

        rows = []
        for emp_id, st in stats.items():
            assigned = st["assigned"]
            completed = st["completed"]
            comp_pct = round((completed / assigned * 100), 2) if assigned > 0 else 0.0
            rows.append({
                "Employee Code": st["employee_code"],
                "Employee Name": st["employee_name"],
                "Team": st["team"],
                "Assigned": assigned,
                "Completed": completed,
                "Pending": st["pending"],
                "Completion %": comp_pct,
                "Outcomes": st["outcomes"],
            })

        headers = ["Employee Code", "Employee Name", "Team", "Assigned", "Completed", "Pending", "Completion %", "Outcomes"]
        resp = export_response(rows, headers, "employee_productivity_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Employee productivity report generated.")


class TeamProductivityReportView(BaseReportView):
    @extend_schema(summary="Team productivity report", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        emp_qs = get_scoped_queryset(request.user, EmployeeProfile.objects.select_related("team").all())

        if request.GET.get("team"):
            emp_qs = emp_qs.filter(team_id=request.GET.get("team"))
        if request.GET.get("department"):
            emp_qs = emp_qs.filter(department_id=request.GET.get("department"))
        if request.GET.get("process"):
            emp_qs = emp_qs.filter(process_id=request.GET.get("process"))

        allocations = ContactAllocation.objects.filter(employee__in=emp_qs)

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            allocations = allocations.filter(allocated_at__date__gte=start_date)
        if end_date:
            allocations = allocations.filter(allocated_at__date__lte=end_date)
        if request.GET.get("task"):
            allocations = allocations.filter(task_id=request.GET.get("task"))

        team_stats = {}
        for alloc in allocations.select_related("employee__team"):
            team_name = alloc.employee.team.name if alloc.employee and alloc.employee.team else "Unassigned"
            if team_name not in team_stats:
                team_stats[team_name] = {"assigned": 0, "completed": 0}
            team_stats[team_name]["assigned"] += 1
            if alloc.status == "COMPLETED":
                team_stats[team_name]["completed"] += 1

        rows = []
        for team_name, st in team_stats.items():
            assigned = st["assigned"]
            completed = st["completed"]
            comp_pct = round((completed / assigned * 100), 2) if assigned > 0 else 0.0
            rows.append({
                "Team": team_name,
                "Assigned": assigned,
                "Completed": completed,
                "Team Completion %": comp_pct,
            })

        headers = ["Team", "Assigned", "Completed", "Team Completion %"]
        resp = export_response(rows, headers, "team_productivity_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Team productivity report generated.")


class TaskAllocationReportView(BaseReportView):
    @extend_schema(summary="Task allocation report", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        task_qs = get_task_scoped_queryset(request.user, Task.objects.select_related("assigned_to", "team").all())

        if request.GET.get("task"):
            task_qs = task_qs.filter(id=request.GET.get("task"))
        if request.GET.get("employee"):
            task_qs = task_qs.filter(assigned_to_id=request.GET.get("employee"))
        if request.GET.get("team"):
            task_qs = task_qs.filter(team_id=request.GET.get("team"))
        if request.GET.get("status"):
            task_qs = task_qs.filter(status=request.GET.get("status"))

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            task_qs = task_qs.filter(created_at__date__gte=start_date)
        if end_date:
            task_qs = task_qs.filter(created_at__date__lte=end_date)

        rows = []
        for t in task_qs:
            allocs = ContactAllocation.objects.filter(task=t)
            total = allocs.count()
            completed = allocs.filter(status="COMPLETED").count()
            pending = allocs.filter(status__in=["PENDING", "IN_PROGRESS"]).count()
            rows.append({
                "Task Title": t.title,
                "Date": str(t.created_at.date()) if t.created_at else "",
                "Deadline": str(t.due_date) if t.due_date else "",
                "Employee": t.assigned_to.user.display_name if t.assigned_to else "",
                "Total Contacts": total,
                "Completed Contacts": completed,
                "Pending Contacts": pending,
                "Status": t.status,
            })

        headers = ["Task Title", "Date", "Deadline", "Employee", "Total Contacts", "Completed Contacts", "Pending Contacts", "Status"]
        resp = export_response(rows, headers, "task_allocation_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Task allocation report generated.")


class ContactOutcomeReportView(BaseReportView):
    @extend_schema(summary="Contact outcome report", tags=["Reports"])
    def get(self, request):
        fmt = request.GET.get("format", "json").lower()
        emp_qs = get_scoped_queryset(request.user, EmployeeProfile.objects.all())
        allocations = ContactAllocation.objects.filter(employee__in=emp_qs).select_related("contact", "employee__user", "task")

        if request.GET.get("employee"):
            allocations = allocations.filter(employee_id=request.GET.get("employee"))
        if request.GET.get("team"):
            allocations = allocations.filter(employee__team_id=request.GET.get("team"))
        if request.GET.get("department"):
            allocations = allocations.filter(employee__department_id=request.GET.get("department"))
        if request.GET.get("process"):
            allocations = allocations.filter(employee__process_id=request.GET.get("process"))
        if request.GET.get("task"):
            allocations = allocations.filter(task_id=request.GET.get("task"))
        if request.GET.get("status"):
            allocations = allocations.filter(status=request.GET.get("status"))

        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            allocations = allocations.filter(allocated_at__date__gte=start_date)
        if end_date:
            allocations = allocations.filter(allocated_at__date__lte=end_date)

        rows = []
        for alloc in allocations:
            rows.append({
                "Contact Name": alloc.contact.full_name,
                "Phone": alloc.contact.phone,
                "Task": alloc.task.title,
                "Assigned Employee": alloc.employee.user.display_name,
                "Outcome Status": alloc.status,
                "Description": alloc.description,
                "Follow Up Date": str(alloc.follow_up_date) if alloc.follow_up_date else "",
                "Updated At": alloc.updated_at.strftime("%Y-%m-%d %H:%M") if alloc.updated_at else "",
            })

        headers = ["Contact Name", "Phone", "Task", "Assigned Employee", "Outcome Status", "Description", "Follow Up Date", "Updated At"]
        resp = export_response(rows, headers, "contact_outcome_report", fmt)
        if resp:
            return resp
        return success_response(rows, "Contact outcome report generated.")


