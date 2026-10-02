from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.attendance.models import Attendance, AttendanceStatus
from apps.attendance.serializers import AttendanceSerializer
from apps.breaks.models import BreakRecord, BreakStatus
from apps.breaks.serializers import BreakRecordSerializer
from apps.breaks.services import calculate_daily_break_duration
from apps.employees.models import EmployeeProfile, EmployeeStatus
from apps.employees.serializers import EmployeeDetailSerializer
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveStatus
from apps.leave.serializers import LeaveBalanceSerializer
from apps.performance.models import PerformanceRecord
from apps.performance.serializers import PerformanceRecordSerializer
from apps.shifts.models import EmployeeShift
from apps.shifts.serializers import EmployeeShiftSerializer
from apps.tasks.models import Task, TaskStatus
from common.exceptions import BusinessRuleError
from common.permissions import (
    IsAdminOrManager,
    IsManagerOrTeamLeader,
    get_employee_scoped_queryset,
    get_scoped_queryset,
    get_task_scoped_queryset,
)
from common.responses import success_response


class EmployeeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Employee Dashboard metrics", tags=["Dashboards"])
    def get(self, request):
        profile = getattr(request.user, "employee_profile", None)
        if not profile:
            raise BusinessRuleError("No employee profile linked to this account.")

        today = timezone.localdate()
        year = today.year

        # Today shift
        shift_assignment = (
            EmployeeShift.objects.filter(employee=profile, effective_from__lte=today)
            .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=today))
            .select_related("shift")
            .order_by("-effective_from")
            .first()
        )

        # Today attendance
        attendance = Attendance.objects.filter(employee=profile, date=today).first()

        # Current break
        active_break = BreakRecord.objects.filter(
            employee=profile, status=BreakStatus.ACTIVE
        ).select_related("break_type").first()

        # Break duration
        total_break_sec = calculate_daily_break_duration(profile, today)

        # Task counts
        task_stats = Task.objects.filter(assigned_to=profile).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            pending=Count("id", filter=Q(status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])),
        )

        # Today performance
        today_perf = PerformanceRecord.objects.filter(
            employee=profile, date=today
        ).select_related("kpi")

        # Leave balances
        leave_balances = LeaveBalance.objects.filter(
            employee=profile, year=year
        ).select_related("leave_type")

        data = {
            "employee": EmployeeDetailSerializer(profile).data,
            "today_shift": EmployeeShiftSerializer(shift_assignment).data if shift_assignment else None,
            "today_attendance": AttendanceSerializer(attendance).data if attendance else None,
            "current_break": BreakRecordSerializer(active_break).data if active_break else None,
            "total_break_duration_seconds": total_break_sec,
            "today_task_count": task_stats["total"] or 0,
            "completed_tasks": task_stats["completed"] or 0,
            "pending_tasks": task_stats["pending"] or 0,
            "today_kpi_performance": PerformanceRecordSerializer(today_perf, many=True).data,
            "leave_balance": LeaveBalanceSerializer(leave_balances, many=True).data,
        }
        return success_response(data, "Employee dashboard retrieved successfully.")


class AdminDashboardView(APIView):
    permission_classes = [IsAdminOrManager]

    @extend_schema(summary="Admin/Manager Dashboard metrics", tags=["Dashboards"])
    def get(self, request):
        user = request.user
        today = timezone.localdate()

        # Employee counts
        emp_qs = get_employee_scoped_queryset(user, EmployeeProfile.objects.all())
        emp_stats = emp_qs.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(status=EmployeeStatus.ACTIVE)),
        )

        # Attendance stats today
        att_qs = get_scoped_queryset(user, Attendance.objects.filter(date=today))
        att_stats = att_qs.aggregate(
            present=Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
            late=Count("id", filter=Q(late_minutes__gt=0)),
        )

        # On break now
        break_qs = get_scoped_queryset(user, BreakRecord.objects.filter(status=BreakStatus.ACTIVE))
        on_break_count = break_qs.count()

        # Tasks stats
        task_qs = get_task_scoped_queryset(user, Task.objects.all())
        task_stats = task_qs.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            pending=Count("id", filter=Q(status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])),
        )

        # Open leave requests
        leave_qs = get_scoped_queryset(user, LeaveRequest.objects.filter(status=LeaveStatus.PENDING))
        open_leaves = leave_qs.count()

        # Performance summary today
        perf_qs = get_scoped_queryset(user, PerformanceRecord.objects.filter(date=today))
        perf_summary = perf_qs.aggregate(
            avg_achievement=Avg("achievement_percentage")
        )

        data = {
            "total_employees": emp_stats["total"] or 0,
            "active_employees": emp_stats["active"] or 0,
            "present_today": att_stats["present"] or 0,
            "absent_today": att_stats["absent"] or 0,
            "late_employees": att_stats["late"] or 0,
            "employees_currently_on_break": on_break_count,
            "total_tasks": task_stats["total"] or 0,
            "completed_tasks": task_stats["completed"] or 0,
            "pending_tasks": task_stats["pending"] or 0,
            "open_leave_requests": open_leaves,
            "performance_summary": {
                "today_avg_achievement_percentage": round(perf_summary["avg_achievement"] or 0.0, 2)
            },
        }
        return success_response(data, "Admin dashboard retrieved successfully.")


class TeamLeaderDashboardView(APIView):
    permission_classes = [IsManagerOrTeamLeader]

    @extend_schema(summary="Team Leader Dashboard metrics", tags=["Dashboards"])
    def get(self, request):
        user = request.user
        today = timezone.localdate()

        # Team leader's teams
        from apps.organization.models import Team
        teams = Team.objects.filter(team_leader=user).select_related("department", "process")
        if not teams.exists() and user.role in ("SUPER_ADMIN", "MANAGER"):
            teams = Team.objects.all()

        team_ids = [t.id for t in teams]

        team_members = EmployeeProfile.objects.filter(team_id__in=team_ids)
        member_ids = list(team_members.values_list("id", flat=True))

        att_stats = Attendance.objects.filter(employee_id__in=member_ids, date=today).aggregate(
            present=Count("id", filter=Q(status=AttendanceStatus.PRESENT)),
            absent=Count("id", filter=Q(status=AttendanceStatus.ABSENT)),
            late=Count("id", filter=Q(late_minutes__gt=0)),
        )

        on_break_count = BreakRecord.objects.filter(
            employee_id__in=member_ids, status=BreakStatus.ACTIVE
        ).count()

        task_stats = Task.objects.filter(team_id__in=team_ids).aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(status=TaskStatus.COMPLETED)),
            pending=Count("id", filter=Q(status__in=[TaskStatus.TODO, TaskStatus.IN_PROGRESS])),
        )

        open_leaves = LeaveRequest.objects.filter(
            employee_id__in=member_ids, status=LeaveStatus.PENDING
        ).count()

        perf_summary = PerformanceRecord.objects.filter(
            employee_id__in=member_ids, date=today
        ).aggregate(avg_achievement=Avg("achievement_percentage"))

        data = {
            "teams_count": len(teams),
            "total_team_members": len(member_ids),
            "present_today": att_stats["present"] or 0,
            "absent_today": att_stats["absent"] or 0,
            "late_today": att_stats["late"] or 0,
            "employees_on_break": on_break_count,
            "total_tasks": task_stats["total"] or 0,
            "completed_tasks": task_stats["completed"] or 0,
            "pending_tasks": task_stats["pending"] or 0,
            "open_leave_requests": open_leaves,
            "today_team_avg_achievement_percentage": round(perf_summary["avg_achievement"] or 0.0, 2),
        }
        return success_response(data, "Team Leader dashboard retrieved successfully.")
