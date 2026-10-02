import pytest

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team
from apps.tasks.models import Task


@pytest.mark.django_db
def test_create_and_assign_task_flow(auth_client, make_user):
    admin = make_user("tsk_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Task Dept")
    proc = make_process(dept, "Task Proc")
    team = make_team(dept, proc, "Task Team")

    emp_payload = {
        "username": "tsk_emp",
        "email": "tsk_emp@example.com",
        "password": "Password123!",
        "first_name": "Task",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_TSK1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="tsk_emp")

    # Create task as admin
    task_res = api_admin.post(
        "/api/tasks/",
        {
            "title": "Resolve Ticket #101",
            "description": "Customer unable to reset password",
            "assigned_to": emp_user.employee_profile.id,
            "priority": "HIGH",
            "due_date": "2026-10-10",
        },
    )
    assert task_res.status_code == 201
    task_id = task_res.data["data"]["id"]
    assert task_res.data["data"]["status"] == "TODO"

    # Login as assigned employee and update status
    api_emp, _, _ = auth_client(emp_user, password="Password123!")

    # Check My Tasks
    my_tasks = api_emp.get("/api/tasks/my/")
    assert my_tasks.status_code == 200
    assert len(my_tasks.data["data"]) == 1

    # Update status to COMPLETED
    status_res = api_emp.patch(f"/api/tasks/{task_id}/status/", {"status": "COMPLETED"})
    assert status_res.status_code == 200
    assert status_res.data["data"]["status"] == "COMPLETED"
    assert status_res.data["data"]["completed_at"] is not None
