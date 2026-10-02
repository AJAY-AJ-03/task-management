import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.leave.models import LeaveType
from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_leave_application_and_approval_flow(auth_client, make_user):
    admin = make_user("lv_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Leave Dept")
    proc = make_process(dept, "Leave Proc")
    team = make_team(dept, proc, "Leave Team")

    emp_payload = {
        "username": "lv_emp",
        "email": "lv_emp@example.com",
        "password": "Password123!",
        "first_name": "Leave",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_LV1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="lv_emp")

    l_type = LeaveType.objects.create(name="Casual Leave", default_days=12)

    # Use separate APIClient for employee
    api_emp = APIClient()
    emp_login = api_emp.post("/api/auth/login/", {"username": "lv_emp", "password": "Password123!"})
    api_emp.credentials(HTTP_AUTHORIZATION=f"Bearer {emp_login.data['data']['access']}")

    # Employee submits leave request for 2 days
    app_res = api_emp.post(
        "/api/leave/requests/",
        {
            "leave_type": l_type.id,
            "start_date": "2026-10-10",
            "end_date": "2026-10-11",
            "reason": "Personal work",
        },
    )
    assert app_res.status_code == 201
    leave_id = app_res.data["data"]["id"]
    assert app_res.data["data"]["status"] == "PENDING"
    assert app_res.data["data"]["total_days"] == "2.0"

    # Admin approves leave request using admin client
    appr_res = api_admin.post(f"/api/leave/requests/{leave_id}/approve/", {})
    assert appr_res.status_code == 200
    assert appr_res.data["data"]["status"] == "APPROVED"

    # Verify updated leave balance for employee
    bal_res = api_emp.get("/api/leave/balance/")
    assert bal_res.status_code == 200
    assert len(bal_res.data["data"]) == 1
    assert bal_res.data["data"][0]["used_days"] == "2.0"
    assert bal_res.data["data"][0]["remaining_days"] == "10.0"
