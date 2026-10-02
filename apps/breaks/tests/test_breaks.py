import pytest

from apps.accounts.models import User
from apps.breaks.models import BreakType
from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_start_and_end_break_flow(auth_client, make_user):
    admin = make_user("brk_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Break Dept")
    proc = make_process(dept, "Break Proc")
    team = make_team(dept, proc, "Break Team")

    emp_payload = {
        "username": "brk_emp",
        "email": "brk_emp@example.com",
        "password": "Password123!",
        "first_name": "Break",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_BRK1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="brk_emp")

    b_type = BreakType.objects.create(name="Tea Break", duration_minutes=15)

    api_emp, _, _ = auth_client(emp_user, password="Password123!")

    # Start break
    start_res = api_emp.post("/api/breaks/start/", {"break_type_id": b_type.id})
    assert start_res.status_code == 200
    assert start_res.data["data"]["status"] == "ACTIVE"

    # End break
    end_res = api_emp.post("/api/breaks/end/", {})
    assert end_res.status_code == 200
    assert end_res.data["data"]["status"] == "COMPLETED"
    assert end_res.data["data"]["end_time"] is not None


@pytest.mark.django_db
def test_prevent_multiple_active_breaks(auth_client, make_user):
    admin = make_user("brk_admin2", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Break Dept 2")
    proc = make_process(dept, "Break Proc 2")
    team = make_team(dept, proc, "Break Team 2")

    emp_payload = {
        "username": "brk_emp2",
        "email": "brk_emp2@example.com",
        "password": "Password123!",
        "first_name": "Break2",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_BRK2",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="brk_emp2")

    b_type = BreakType.objects.create(name="Lunch", duration_minutes=45)

    api_emp, _, _ = auth_client(emp_user, password="Password123!")

    # First start break
    api_emp.post("/api/breaks/start/", {"break_type_id": b_type.id})

    # Second start break attempt should fail
    start2 = api_emp.post("/api/breaks/start/", {"break_type_id": b_type.id})
    assert start2.status_code == 400
    assert start2.data["success"] is False
