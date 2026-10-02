import pytest
from datetime import date, time
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import User, Role
from apps.attendance.models import Attendance, AttendanceStatus
from apps.breaks.models import BreakRecord, BreakStatus, BreakType
from apps.employees.models import EmployeeProfile
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType
from apps.organization.models import Department, Process, Team
from apps.performance.models import KPI, PerformanceRecord
from apps.permissions_app.models import PermissionRequest
from apps.tasks.models import Task, TaskPriority, TaskStatus


def setup_rbac_test_domain(make_user):
    # Super Admin
    super_admin = make_user("superadmin_test", role=Role.SUPER_ADMIN)

    # Department and Process
    dept = Department.objects.create(name="Support Operations")
    proc = Process.objects.create(department=dept, name="Inbound Voice")

    # Manager A & Team Leader A & Team A
    manager_a = make_user("manager_a", role=Role.MANAGER)
    tl_a = make_user("tleader_a", role=Role.TEAM_LEADER)
    team_a = Team.objects.create(name="Team A", department=dept, process=proc, manager=manager_a, team_leader=tl_a)

    # Employee A (in Team A)
    user_emp_a = make_user("employee_a", role=Role.EMPLOYEE)
    emp_a = EmployeeProfile.objects.create(
        user=user_emp_a,
        employee_code="EMPA01",
        date_of_joining=date(2026, 1, 1),
        designation="Agent A",
        department=dept,
        process=proc,
        team=team_a,
        reporting_manager=manager_a,
        team_leader=tl_a,
    )

    # Manager B & Team Leader B & Team B
    manager_b = make_user("manager_b", role=Role.MANAGER)
    tl_b = make_user("tleader_b", role=Role.TEAM_LEADER)
    team_b = Team.objects.create(name="Team B", department=dept, process=proc, manager=manager_b, team_leader=tl_b)

    # Employee B (in Team B)
    user_emp_b = make_user("employee_b", role=Role.EMPLOYEE)
    emp_b = EmployeeProfile.objects.create(
        user=user_emp_b,
        employee_code="EMPB01",
        date_of_joining=date(2026, 1, 1),
        designation="Agent B",
        department=dept,
        process=proc,
        team=team_b,
        reporting_manager=manager_b,
        team_leader=tl_b,
    )

    return {
        "super_admin": super_admin,
        "manager_a": manager_a,
        "tl_a": tl_a,
        "team_a": team_a,
        "emp_a": emp_a,
        "user_emp_a": user_emp_a,
        "manager_b": manager_b,
        "tl_b": tl_b,
        "team_b": team_b,
        "emp_b": emp_b,
        "user_emp_b": user_emp_b,
    }


@pytest.mark.django_db
def test_performance_rbac_scoping_and_idor(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    kpi = KPI.objects.create(name="Calls Handled", default_target=Decimal("100.00"))

    perf_a = PerformanceRecord.objects.create(
        employee=d["emp_a"], kpi=kpi, date=date.today(), target_value=Decimal("100.00"), actual_value=Decimal("95.00")
    )
    perf_b = PerformanceRecord.objects.create(
        employee=d["emp_b"], kpi=kpi, date=date.today(), target_value=Decimal("100.00"), actual_value=Decimal("80.00")
    )

    # Employee A: list contains only own record, getting perf_b resolves as 404
    api_emp_a, _, _ = auth_client(d["user_emp_a"])
    res_list = api_emp_a.get("/api/performance/")
    assert res_list.status_code == 200
    ids = [r["id"] for r in res_list.data["data"]]
    assert perf_a.id in ids
    assert perf_b.id not in ids

    res_idor = api_emp_a.get(f"/api/performance/{perf_b.id}/")
    assert res_idor.status_code == 404

    # Team Leader A: sees perf_a, cannot see perf_b
    api_tl_a, _, _ = auth_client(d["tl_a"])
    res_tl = api_tl_a.get("/api/performance/")
    assert res_tl.status_code == 200
    ids_tl = [r["id"] for r in res_tl.data["data"]]
    assert perf_a.id in ids_tl
    assert perf_b.id not in ids_tl

    # Manager A: sees perf_a, cannot see perf_b
    api_mgr_a, _, _ = auth_client(d["manager_a"])
    res_mgr = api_mgr_a.get("/api/performance/")
    assert res_mgr.status_code == 200
    ids_mgr = [r["id"] for r in res_mgr.data["data"]]
    assert perf_a.id in ids_mgr
    assert perf_b.id not in ids_mgr

    # Super Admin: sees all
    api_admin, _, _ = auth_client(d["super_admin"])
    res_admin = api_admin.get("/api/performance/")
    assert res_admin.status_code == 200
    ids_admin = [r["id"] for r in res_admin.data["data"]]
    assert perf_a.id in ids_admin
    assert perf_b.id in ids_admin


@pytest.mark.django_db
def test_employee_rbac_scoping(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)

    # Manager A only sees employee A
    api_mgr_a, _, _ = auth_client(d["manager_a"])
    res_mgr = api_mgr_a.get("/api/employees/")
    assert res_mgr.status_code == 200
    codes = [e["employee_code"] for e in res_mgr.data["data"]]
    assert "EMPA01" in codes
    assert "EMPB01" not in codes

    # Manager A cannot view Employee B detail endpoint (404)
    res_detail = api_mgr_a.get(f"/api/employees/{d['emp_b'].id}/")
    assert res_detail.status_code == 404

    # Team Leader A only sees employee A
    api_tl_a, _, _ = auth_client(d["tl_a"])
    res_tl = api_tl_a.get("/api/employees/")
    assert res_tl.status_code == 200
    codes_tl = [e["employee_code"] for e in res_tl.data["data"]]
    assert "EMPA01" in codes_tl
    assert "EMPB01" not in codes_tl


@pytest.mark.django_db
def test_employee_shift_assignment_scope(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    from apps.shifts.models import Shift
    shift = Shift.objects.create(name="Morning Shift", start_time=time(9, 0), end_time=time(17, 0))

    api_mgr_a, _, _ = auth_client(d["manager_a"])

    # Assigning to Employee A (inside scope) -> allowed
    res_a = api_mgr_a.post("/api/employee-shifts/", {
        "employee": d["emp_a"].id,
        "shift": shift.id,
        "effective_from": "2026-03-01",
    })
    assert res_a.status_code == 201

    # Assigning to Employee B (outside scope) -> denied
    res_b = api_mgr_a.post("/api/employee-shifts/", {
        "employee": d["emp_b"].id,
        "shift": shift.id,
        "effective_from": "2026-03-01",
    })
    assert res_b.status_code == 400


@pytest.mark.django_db
def test_attendance_rbac_scoping_and_idor(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    att_a = Attendance.objects.create(employee=d["emp_a"], date=date.today(), status=AttendanceStatus.PRESENT)
    att_b = Attendance.objects.create(employee=d["emp_b"], date=date.today(), status=AttendanceStatus.PRESENT)

    api_tl_a, _, _ = auth_client(d["tl_a"])

    # TL A gets attendance list -> only att_a
    res_list = api_tl_a.get("/api/attendance/")
    assert res_list.status_code == 200
    ids = [a["id"] for a in res_list.data["data"]]
    assert att_a.id in ids
    assert att_b.id not in ids

    # TL A trying to view att_b detail -> 404
    res_detail = api_tl_a.get(f"/api/attendance/{att_b.id}/")
    assert res_detail.status_code == 404


@pytest.mark.django_db
def test_task_rbac_scoping_and_reassignment_boundary(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    task_a = Task.objects.create(title="Task A", assigned_to=d["emp_a"], team=d["team_a"], assigned_by=d["manager_a"])
    task_b = Task.objects.create(title="Task B", assigned_to=d["emp_b"], team=d["team_b"], assigned_by=d["manager_b"])

    api_tl_a, _, _ = auth_client(d["tl_a"])

    # TL A reassigning Task A to Employee A -> allowed
    res_ok = api_tl_a.patch(f"/api/tasks/{task_a.id}/assign/", {"assigned_to": d["emp_a"].id})
    assert res_ok.status_code == 200

    # TL A reassigning Task A to Employee B (outside team) -> denied
    res_denied = api_tl_a.patch(f"/api/tasks/{task_a.id}/assign/", {"assigned_to": d["emp_b"].id})
    assert res_denied.status_code == 400


@pytest.mark.django_db
def test_leave_request_approval_rejection_cancellation_scope(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    ltype = LeaveType.objects.create(name="Casual Leave", default_days=12)

    LeaveBalance.objects.create(
        employee=d["emp_a"], leave_type=ltype, year=2026, allocated_days=Decimal("12.0"), used_days=Decimal("0.0"), remaining_days=Decimal("12.0")
    )
    LeaveBalance.objects.create(
        employee=d["emp_b"], leave_type=ltype, year=2026, allocated_days=Decimal("12.0"), used_days=Decimal("0.0"), remaining_days=Decimal("12.0")
    )

    leave_a = LeaveRequest.objects.create(
        employee=d["emp_a"], leave_type=ltype, start_date=date(2026, 4, 1), end_date=date(2026, 4, 2), reason="Personal"
    )
    leave_b = LeaveRequest.objects.create(
        employee=d["emp_b"], leave_type=ltype, start_date=date(2026, 4, 1), end_date=date(2026, 4, 2), reason="Personal"
    )

    api_tl_a, _, _ = auth_client(d["tl_a"])

    # TL A approves leave_a -> allowed
    res_app = api_tl_a.post(f"/api/leave/requests/{leave_a.id}/approve/")
    assert res_app.status_code == 200

    # TL A approves leave_b -> denied (404 because leave_b is outside TL A's scoped queryset)
    res_denied = api_tl_a.post(f"/api/leave/requests/{leave_b.id}/approve/")
    assert res_denied.status_code == 404


@pytest.mark.django_db
def test_permission_request_approval_rejection_scope(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    perm_a = PermissionRequest.objects.create(
        employee=d["emp_a"], date=date.today(), start_time=time(10, 0), end_time=time(11, 0), reason="Doctor Visit"
    )
    perm_b = PermissionRequest.objects.create(
        employee=d["emp_b"], date=date.today(), start_time=time(10, 0), end_time=time(11, 0), reason="Doctor Visit"
    )

    api_mgr_a, _, _ = auth_client(d["manager_a"])

    # Manager A approves perm_a -> allowed
    res_app = api_mgr_a.post(f"/api/permissions/{perm_a.id}/approve/")
    assert res_app.status_code == 200

    # Manager A approves perm_b -> 404
    res_denied = api_mgr_a.post(f"/api/permissions/{perm_b.id}/approve/")
    assert res_denied.status_code == 404


@pytest.mark.django_db
def test_team_employees_endpoint_authorization(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)

    api_emp_a, _, _ = auth_client(d["user_emp_a"])

    # Employee A accessing own team employees -> allowed
    res_own = api_emp_a.get(f"/api/teams/{d['team_a'].id}/employees/")
    assert res_own.status_code == 200

    # Employee A accessing Team B employees -> denied (404)
    res_other = api_emp_a.get(f"/api/teams/{d['team_b'].id}/employees/")
    assert res_other.status_code == 404


@pytest.mark.django_db
def test_reports_rbac_scoping_and_query_param_bypass_protection(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    Attendance.objects.create(employee=d["emp_a"], date=date.today(), status=AttendanceStatus.PRESENT)
    Attendance.objects.create(employee=d["emp_b"], date=date.today(), status=AttendanceStatus.PRESENT)

    # Employee calling report -> 403
    api_emp_a, _, _ = auth_client(d["user_emp_a"])
    res_emp = api_emp_a.get("/api/reports/attendance/")
    assert res_emp.status_code == 403

    # Team Leader A calling report -> receives only Team A data
    api_tl_a, _, _ = auth_client(d["tl_a"])
    res_tl = api_tl_a.get("/api/reports/attendance/")
    assert res_tl.status_code == 200
    rows = res_tl.data["data"]
    codes = [r["Employee Code"] for r in rows]
    assert "EMPA01" in codes
    assert "EMPB01" not in codes

    # Team Leader A supplying ?team=<Team B ID> query parameter bypass attempt
    res_bypass = api_tl_a.get(f"/api/reports/attendance/?team={d['team_b'].id}")
    assert res_bypass.status_code == 200
    # Should return empty list because Team B is outside TL A's authorization scope
    assert len(res_bypass.data["data"]) == 0


@pytest.mark.django_db
def test_admin_dashboard_manager_scoping(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    Attendance.objects.create(employee=d["emp_a"], date=date.today(), status=AttendanceStatus.PRESENT)
    Attendance.objects.create(employee=d["emp_b"], date=date.today(), status=AttendanceStatus.PRESENT)

    api_mgr_a, _, _ = auth_client(d["manager_a"])
    res = api_mgr_a.get("/api/dashboard/admin/")
    assert res.status_code == 200
    # Total employees in Manager A scope is 1 (Employee A)
    assert res.data["data"]["total_employees"] == 1
    assert res.data["data"]["present_today"] == 1


@pytest.mark.django_db
def test_privilege_escalation_manager_creating_super_admin_or_manager(auth_client, make_user):
    d = setup_rbac_test_domain(make_user)
    api_mgr_a, _, _ = auth_client(d["manager_a"])

    payload_admin = {
        "username": "hacked_admin",
        "email": "hacked_admin@example.com",
        "password": "Password123!",
        "first_name": "Hacked",
        "last_name": "Admin",
        "role": "SUPER_ADMIN",
        "employee_code": "BAD001",
        "date_of_joining": "2026-01-01",
        "designation": "Manager",
        "department": d["emp_a"].department_id,
        "process": d["emp_a"].process_id,
        "team": d["emp_a"].team_id,
        "status": "ACTIVE",
    }

    # Attempt to create SUPER_ADMIN -> denied (400)
    res_admin = api_mgr_a.post("/api/employees/", payload_admin)
    assert res_admin.status_code == 400
    assert "role" in res_admin.data["errors"]

    # Attempt to create MANAGER -> denied (400)
    payload_mgr = dict(payload_admin, username="hacked_mgr", email="hacked_mgr@example.com", role="MANAGER", employee_code="BAD002")
    res_mgr = api_mgr_a.post("/api/employees/", payload_mgr)
    assert res_mgr.status_code == 400
    assert "role" in res_mgr.data["errors"]
