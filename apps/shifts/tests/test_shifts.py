import pytest
from django.utils import timezone

from apps.organization.tests.factories import make_department, make_process, make_team
from apps.shifts.models import Shift


@pytest.mark.django_db
def test_admin_can_create_shift(auth_client, make_user):
    admin = make_user("shift_admin", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)

    res = api.post(
        "/api/shifts/",
        {
            "name": "Morning Shift",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "break_duration_minutes": 60,
        },
    )
    assert res.status_code == 201
    assert res.data["data"]["name"] == "Morning Shift"
    assert res.data["data"]["is_overnight"] is False


@pytest.mark.django_db
def test_overnight_shift_flag_auto_detected(auth_client, make_user):
    admin = make_user("shift_admin2", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)

    res = api.post(
        "/api/shifts/",
        {
            "name": "Night Shift",
            "start_time": "22:00:00",
            "end_time": "07:00:00",
            "break_duration_minutes": 60,
        },
    )
    assert res.status_code == 201
    assert res.data["data"]["is_overnight"] is True


@pytest.mark.django_db
def test_assign_shift_and_prevent_overlap(auth_client, make_user):
    admin = make_user("shift_admin3", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Dept S")
    proc = make_process(dept, "Proc S")
    team = make_team(dept, proc, "Team S")

    # Create employee via API
    emp_payload = {
        "username": "shift_emp",
        "email": "shift_emp@example.com",
        "password": "Password123!",
        "first_name": "Shift",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_S1",
        "date_of_joining": "2026-01-01",
        "designation": "Executive",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9999999999",
        "status": "ACTIVE",
    }
    emp_res = api_admin.post("/api/employees/", emp_payload)
    assert emp_res.status_code == 201
    emp_id = emp_res.data["data"]["id"]

    shift = Shift.objects.create(
        name="General Shift", start_time="09:00:00", end_time="18:00:00"
    )

    # First shift assignment (open ended)
    assign_res = api_admin.post(
        "/api/employee-shifts/",
        {
            "employee": emp_id,
            "shift": shift.id,
            "effective_from": "2026-01-01",
        },
    )
    assert assign_res.status_code == 201

    # Overlapping assignment attempt should fail with 400 validation error
    overlap_res = api_admin.post(
        "/api/employee-shifts/",
        {
            "employee": emp_id,
            "shift": shift.id,
            "effective_from": "2026-02-01",
        },
    )
    assert overlap_res.status_code == 400
    assert "effective_from" in overlap_res.data["errors"]
