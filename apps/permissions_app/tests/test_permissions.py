import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_permission_request_flow(auth_client, make_user):
    admin = make_user("prm_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Perm Dept")
    proc = make_process(dept, "Perm Proc")
    team = make_team(dept, proc, "Perm Team")

    emp_payload = {
        "username": "prm_emp",
        "email": "prm_emp@example.com",
        "password": "Password123!",
        "first_name": "Perm",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_PRM1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="prm_emp")

    # Use separate APIClient for employee
    api_emp = APIClient()
    emp_login = api_emp.post("/api/auth/login/", {"username": "prm_emp", "password": "Password123!"})
    api_emp.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['data']['access']}")

    # Submit permission request
    req_res = api_emp.post(
        "/api/permissions/",
        {
            "date": "2026-10-15",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "reason": "Doctor appointment",
        },
    )
    assert req_res.status_code == 201
    perm_id = req_res.data["data"]["id"]
    assert req_res.data["data"]["duration_minutes"] == 120
    assert req_res.data["data"]["status"] == "PENDING"

    # Admin approves request
    appr_res = api_admin.post(f"/api/permissions/{perm_id}/approve/", {})
    assert appr_res.status_code == 200
    assert appr_res.data["data"]["status"] == "APPROVED"
