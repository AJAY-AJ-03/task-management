import pytest

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_admin_dashboard_metrics(auth_client, make_user):
    admin = make_user("dsh_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    res = api_admin.get("/api/dashboard/admin/")
    assert res.status_code == 200
    data = res.data["data"]
    assert "total_employees" in data
    assert "active_employees" in data
    assert "present_today" in data
    assert "open_leave_requests" in data


@pytest.mark.django_db
def test_employee_dashboard_metrics(auth_client, make_user):
    admin = make_user("dsh_admin2", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Dash Dept")
    proc = make_process(dept, "Dash Proc")
    team = make_team(dept, proc, "Dash Team")

    emp_payload = {
        "username": "dsh_emp",
        "email": "dsh_emp@example.com",
        "password": "Password123!",
        "first_name": "Dash",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_DSH1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="dsh_emp")

    api_emp, _, _ = auth_client(emp_user, password="Password123!")
    res = api_emp.get("/api/dashboard/employee/")
    assert res.status_code == 200
    data = res.data["data"]
    assert data["employee"]["employee_code"] == "EMP_DSH1"
    assert "today_attendance" in data
    assert "leave_balance" in data
