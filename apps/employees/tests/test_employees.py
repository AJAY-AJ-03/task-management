import pytest

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_admin_can_create_employee_profile(auth_client, make_user):
    admin = make_user("admin_emp", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)

    dept = make_department("Customer Service")
    proc = make_process(dept, "Voice Support")
    team = make_team(dept, proc, "Alpha Team")

    payload = {
        "username": "newemp",
        "email": "newemp@example.com",
        "password": "Password123!",
        "first_name": "New",
        "last_name": "Employee",
        "role": "EMPLOYEE",
        "employee_code": "EMP100",
        "date_of_joining": "2026-01-15",
        "designation": "Customer Support Executive",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }

    res = api.post("/api/employees/", payload)
    assert res.status_code == 201
    assert res.data["data"]["employee_code"] == "EMP100"
    assert res.data["data"]["user"]["employee_id"] == "EMP100"


@pytest.mark.django_db
def test_employee_cannot_create_other_employees(auth_client):
    api, _, _ = auth_client()
    res = api.post("/api/employees/", {})
    assert res.status_code == 403


@pytest.mark.django_db
def test_employee_me_endpoint(auth_client, make_user):
    admin = make_user("admin_me", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Sales Dept")
    proc = make_process(dept, "Inbound Sales")
    team = make_team(dept, proc, "Sales Team")

    payload = {
        "username": "emp_me_user",
        "email": "emp_me_user@example.com",
        "password": "Password123!",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "EMPLOYEE",
        "employee_code": "EMP200",
        "date_of_joining": "2026-02-01",
        "designation": "Sales Executive",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9123456789",
        "status": "ACTIVE",
    }
    # Create profile as admin first
    create_res = api_admin.post("/api/employees/", payload)
    assert create_res.status_code == 201

    emp_user = User.objects.get(username="emp_me_user")
    # Now login as emp_user and call /api/employees/me/
    api_emp, _, _ = auth_client(emp_user, password="Password123!")
    me_res = api_emp.get("/api/employees/me/")
    assert me_res.status_code == 200
    assert me_res.data["data"]["employee_code"] == "EMP200"

    # Self-update contact info
    patch_res = api_emp.patch(
        "/api/employees/me/",
        {"emergency_contact_name": "John Doe", "emergency_contact_phone": "9998887776"},
    )
    assert patch_res.status_code == 200
    assert patch_res.data["data"]["emergency_contact_name"] == "John Doe"
