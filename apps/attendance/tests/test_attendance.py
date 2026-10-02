import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team
from apps.shifts.models import EmployeeShift, Shift


@pytest.mark.django_db
def test_check_in_and_check_out_flow(auth_client, make_user):
    admin = make_user("att_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Support")
    proc = make_process(dept, "Voice")
    team = make_team(dept, proc, "Team Voice")

    emp_payload = {
        "username": "att_emp",
        "email": "att_emp@example.com",
        "password": "Password123!",
        "first_name": "Att",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_ATT1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    emp_res = api_admin.post("/api/employees/", emp_payload)
    assert emp_res.status_code == 201
    emp_user = User.objects.get(username="att_emp")

    shift = Shift.objects.create(name="Morning Shift", start_time="09:00:00", end_time="18:00:00")
    EmployeeShift.objects.create(
        employee=emp_user.employee_profile, shift=shift, effective_from="2026-01-01"
    )

    api_emp, _, _ = auth_client(emp_user, password="Password123!")

    # Check-in
    in_res = api_emp.post("/api/attendance/check-in/", {"remarks": "On time"})
    assert in_res.status_code == 200
    assert in_res.data["data"]["status"] == "PRESENT"
    assert in_res.data["data"]["check_in"] is not None

    # Check-out
    out_res = api_emp.post("/api/attendance/check-out/", {})
    assert out_res.status_code == 200
    assert out_res.data["data"]["check_out"] is not None


@pytest.mark.django_db
def test_duplicate_check_in_rejected(auth_client, make_user):
    admin = make_user("att_admin2", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Support 2")
    proc = make_process(dept, "Email")
    team = make_team(dept, proc, "Team Email")

    emp_payload = {
        "username": "att_emp2",
        "email": "att_emp2@example.com",
        "password": "Password123!",
        "first_name": "Att2",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_ATT2",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="att_emp2")

    api_emp, _, _ = auth_client(emp_user, password="Password123!")

    # First check-in
    res1 = api_emp.post("/api/attendance/check-in/", {})
    assert res1.status_code == 200

    # Second check-in on same day should fail
    res2 = api_emp.post("/api/attendance/check-in/", {})
    assert res2.status_code == 400
    assert res2.data["success"] is False
