import pytest

from .factories import make_department, make_process, make_team


@pytest.mark.django_db
def test_employee_cannot_create_department(auth_client):
    api, _, _ = auth_client()
    res = api.post("/api/departments/", {"name": "Sales"})
    assert res.status_code == 403


@pytest.mark.django_db
def test_admin_can_create_and_list_department(auth_client, make_user):
    admin = make_user("admin1", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)
    res = api.post("/api/departments/", {"name": "Technical Support", "description": "Tech support dept"})
    assert res.status_code == 201
    assert res.data["data"]["name"] == "Technical Support"

    list_res = api.get("/api/departments/")
    assert list_res.status_code == 200
    assert len(list_res.data["data"]) == 1


@pytest.mark.django_db
def test_process_must_belong_to_department(auth_client, make_user):
    admin = make_user("admin2", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)
    dept_a = make_department("Dept A")
    dept_b = make_department("Dept B")
    process_b = make_process(dept_b, "Process B")
    res = api.post(
        "/api/teams/",
        {
            "name": "Mismatched",
            "department": dept_a.id,
            "process": process_b.id,
        },
    )
    assert res.status_code == 400
    assert "process" in res.data["errors"]


@pytest.mark.django_db
def test_team_employees_action_lists_members(auth_client, make_user):
    admin = make_user("admin3", role="SUPER_ADMIN")
    api, _, _ = auth_client(admin)
    team = make_team()
    res = api.get(f"/api/teams/{team.id}/employees/")
    assert res.status_code == 200
    assert res.data["data"] == []