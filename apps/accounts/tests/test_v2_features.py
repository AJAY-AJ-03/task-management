import io
import openpyxl
import pytest
from datetime import date, timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import User, Role
from apps.contacts.models import Contact, ContactAllocation, ContactAllocationStatus, ContactImport
from apps.employees.models import EmployeeProfile
from apps.escalations.models import Escalation, EscalationStatus
from apps.feedback.models import Feedback, FeedbackStatus
from apps.organization.models import Department, Process, Team
from apps.sop.models import SOP, SOPStatus
from apps.tasks.models import Task, TaskActivity, TaskPriority, TaskStatus
from common.exceptions import BusinessRuleError


def setup_v2_domain(make_user):
    # Department & Process
    dept = Department.objects.create(name="Customer Ops")
    proc = Process.objects.create(department=dept, name="Voice Support")

    # Manager A & TL A & Team A
    manager_a = make_user("manager_v2_a", role=Role.MANAGER)
    tl_a = make_user("tleader_v2_a", role=Role.TEAM_LEADER)
    team_a = Team.objects.create(name="Team V2 A", department=dept, process=proc, manager=manager_a, team_leader=tl_a)

    # Employees in Team A
    u_emp_a1 = make_user("emp_v2_a1", role=Role.EMPLOYEE)
    emp_a1 = EmployeeProfile.objects.create(
        user=u_emp_a1, employee_code="EV2A01", date_of_joining=date(2026, 1, 1), designation="Agent A1",
        department=dept, process=proc, team=team_a, reporting_manager=manager_a, team_leader=tl_a
    )

    u_emp_a2 = make_user("emp_v2_a2", role=Role.EMPLOYEE)
    emp_a2 = EmployeeProfile.objects.create(
        user=u_emp_a2, employee_code="EV2A02", date_of_joining=date(2026, 1, 1), designation="Agent A2",
        department=dept, process=proc, team=team_a, reporting_manager=manager_a, team_leader=tl_a
    )

    # Manager B & Team B
    manager_b = make_user("manager_v2_b", role=Role.MANAGER)
    tl_b = make_user("tleader_v2_b", role=Role.TEAM_LEADER)
    team_b = Team.objects.create(name="Team V2 B", department=dept, process=proc, manager=manager_b, team_leader=tl_b)

    u_emp_b1 = make_user("emp_v2_b1", role=Role.EMPLOYEE)
    emp_b1 = EmployeeProfile.objects.create(
        user=u_emp_b1, employee_code="EV2B01", date_of_joining=date(2026, 1, 1), designation="Agent B1",
        department=dept, process=proc, team=team_b, reporting_manager=manager_b, team_leader=tl_b
    )

    return {
        "dept": dept, "proc": proc,
        "manager_a": manager_a, "tl_a": tl_a, "team_a": team_a, "emp_a1": emp_a1, "emp_a2": emp_a2,
        "manager_b": manager_b, "tl_b": tl_b, "team_b": team_b, "emp_b1": emp_b1
    }


def generate_excel_file(headers, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


@pytest.mark.django_db
class TestV2Features:

    def test_sop_permissions_and_scoping(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        # Create SOP as Manager A
        client_mgr, _, _ = auth_client(d["manager_a"])
        sop_data = {
            "title": "Standard Support SOP",
            "content": "Step 1: Greet customer. Step 2: Resolve issue.",
            "category": "Customer Support",
            "status": SOPStatus.PUBLISHED,
            "department": d["dept"].id,
            "process": d["proc"].id,
            "team": d["team_a"].id,
        }
        res = client_mgr.post("/api/sops/", sop_data, format="json")
        assert res.status_code == 201
        sop_id = res.data["data"]["id"]

        # Create Draft SOP
        draft_sop = SOP.objects.create(
            title="Draft Policy", content="Under review", category="Policy",
            status=SOPStatus.DRAFT, created_by=d["manager_a"]
        )

        # Employee A1 views published SOPs
        client_emp1, _, _ = auth_client(d["emp_a1"].user)
        res_list = client_emp1.get("/api/sops/")
        assert res_list.status_code == 200
        titles = [s["title"] for s in res_list.data["data"]]
        assert "Standard Support SOP" in titles
        assert "Draft Policy" not in titles

        # Employee B1 views SOPs (Team B vs Team A scoping)
        client_emp_b, _, _ = auth_client(d["emp_b1"].user)
        res_b = client_emp_b.get("/api/sops/")
        titles_b = [s["title"] for s in res_b.data["data"]]
        assert "Standard Support SOP" not in titles_b

        # Employee attempts to create SOP -> 403
        res_fail = client_emp1.post("/api/sops/", sop_data, format="json")
        assert res_fail.status_code == 403

    def test_escalation_management_flow_and_scoping(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        # Employee A1 creates Escalation
        client_emp1, _, _ = auth_client(d["emp_a1"].user)
        esc_payload = {
            "title": "High Priority System Outage",
            "description": "CRM is down for inbound calls",
            "priority": "HIGH",
        }
        res = client_emp1.post("/api/escalations/", esc_payload, format="json")
        assert res.status_code == 201
        esc_id = res.data["data"]["id"]

        # Employee B1 cannot see Employee A1's escalation
        client_emp_b, _, _ = auth_client(d["emp_b1"].user)
        res_b = client_emp_b.get("/api/escalations/")
        assert len(res_b.data["data"]) == 0

        # Manager A updates and resolves escalation
        client_mgr, _, _ = auth_client(d["manager_a"])
        patch_res = client_mgr.patch(f"/api/escalations/{esc_id}/", {
            "status": EscalationStatus.RESOLVED,
            "assigned_to": d["emp_a2"].id,
            "resolution_notes": "Database connection restored",
        }, format="json")
        assert patch_res.status_code == 200
        assert patch_res.data["data"]["status"] == EscalationStatus.RESOLVED

    def test_feedback_privacy_and_management(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        client_emp1, _, _ = auth_client(d["emp_a1"].user)
        fb_payload = {
            "category": "Facility",
            "subject": "Headset noise issue",
            "description": "Noise cancellation is broken on unit 4",
            "rating": 2,
        }
        res = client_emp1.post("/api/feedback/", fb_payload, format="json")
        assert res.status_code == 201
        fb_id = res.data["data"]["id"]

        # Employee B1 cannot see Employee A1's feedback
        client_emp_b, _, _ = auth_client(d["emp_b1"].user)
        res_b = client_emp_b.get("/api/feedback/")
        assert len(res_b.data["data"]) == 0

        # Manager A reviews and responds
        client_mgr, _, _ = auth_client(d["manager_a"])
        patch_res = client_mgr.patch(f"/api/feedback/{fb_id}/", {
            "status": FeedbackStatus.REVIEWED,
            "response": "New headset dispatched",
        }, format="json")
        assert patch_res.status_code == 200
        assert patch_res.data["data"]["response"] == "New headset dispatched"

    def test_task_activity_immutability(self, make_user):
        d = setup_v2_domain(make_user)
        task = Task.objects.create(
            title="Audit Task", assigned_to=d["emp_a1"], assigned_by=d["manager_a"],
            team=d["team_a"], priority=TaskPriority.HIGH, status=TaskStatus.TODO
        )
        activity = TaskActivity.objects.create(
            task=task, actor=d["manager_a"], action="CREATED", description="Task created"
        )
        assert activity.id is not None

        # Attempt to modify activity raises BusinessRuleError
        activity.description = "Modified description"
        with pytest.raises(BusinessRuleError):
            activity.save()

        # Attempt to delete activity raises BusinessRuleError
        with pytest.raises(BusinessRuleError):
            activity.delete()

    def test_excel_upload_and_import(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        client_mgr, _, _ = auth_client(d["manager_a"])

        headers = ["first_name", "last_name", "phone", "email", "city", "notes"]
        rows = [
            ["John", "Doe", "9876543210", "john@example.com", "NYC", "Lead 1"],
            ["Jane", "Smith", "9876543211", "jane@example.com", "LA", "Lead 2"],
            ["Alice", "Brown", "9876543212", "alice@example.com", "Chicago", "Lead 3"],
            ["Bob", "White", "9876543213", "bob@example.com", "Houston", "Lead 4"],
            ["Charlie", "Green", "9876543214", "charlie@example.com", "Phoenix", "Lead 5"],
            ["Eve", "Black", "9876543215", "eve@example.com", "Dallas", "Lead 6"],
            ["Grace", "Hopper", "9876543216", "grace@example.com", "Austin", "Lead 7"],
            ["Alan", "Turing", "9876543217", "alan@example.com", "Burbank", "Lead 8"],
            ["Ada", "Lovelace", "9876543218", "ada@example.com", "London", "Lead 9"],
            ["Linus", "Torvalds", "9876543219", "linus@example.com", "Helsinki", "Lead 10"],
        ]
        file_bytes = generate_excel_file(headers, rows)
        uploaded = SimpleUploadedFile("contacts.xlsx", file_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        res = client_mgr.post("/api/contacts/upload/", {"file": uploaded}, format="multipart")
        assert res.status_code == 201
        assert res.data["data"]["success_rows"] == 10
        assert res.data["data"]["failed_rows"] == 0

        # Duplicate check test
        res_dup = client_mgr.post("/api/contacts/upload/", {"file": uploaded}, format="multipart")
        assert res_dup.status_code == 400

    def test_contact_allocation_split_and_progress(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        client_mgr, _, _ = auth_client(d["manager_a"])

        # Create 10 contacts manually
        contacts = []
        for i in range(10):
            c = Contact.objects.create(
                first_name=f"Lead{i}", phone=f"900000000{i}", email=f"lead{i}@test.com"
            )
            contacts.append(c.id)

        # Allocate 10 contacts to 2 employees (emp_a1 and emp_a2)
        alloc_payload = {
            "title": "Outbound Campaign 1",
            "date": str(date.today()),
            "deadline": str(timezone.now() + timedelta(days=1)),
            "employee_ids": [d["emp_a1"].id, d["emp_a2"].id],
            "contact_ids": contacts,
            "notes": "Call all leads",
        }
        res_alloc = client_mgr.post("/api/contacts/allocate/", alloc_payload, format="json")
        assert res_alloc.status_code == 201
        task_id = res_alloc.data["data"]["task_id"]

        # Check allocations (5 each)
        allocs_a1 = ContactAllocation.objects.filter(employee=d["emp_a1"], task_id=task_id)
        allocs_a2 = ContactAllocation.objects.filter(employee=d["emp_a2"], task_id=task_id)
        assert allocs_a1.count() == 5
        assert allocs_a2.count() == 5

        # Employee A1 views assigned contacts
        client_emp1, _, _ = auth_client(d["emp_a1"].user)
        res_my = client_emp1.get("/api/contacts/my-allocations/")
        assert res_my.status_code == 200
        assert len(res_my.data["data"]) == 5

        # Employee A1 processes contacts
        alloc1 = allocs_a1[0]
        patch_alloc = client_emp1.patch(f"/api/contacts/allocations/{alloc1.id}/status/", {
            "status": "COMPLETED",
            "description": "Customer interested in plan",
        }, format="json")
        assert patch_alloc.status_code == 200

        # Check task progress view
        res_prog = client_mgr.get(f"/api/tasks/{task_id}/progress/")
        assert res_prog.status_code == 200
        assert res_prog.data["data"]["completed"] == 1
        assert res_prog.data["data"]["pending"] == 9
        assert res_prog.data["data"]["completion_percentage"] == 10.0
        assert res_prog.data["data"]["overall_status"] == TaskStatus.IN_PROGRESS

        # Complete all remaining allocations
        for alloc in ContactAllocation.objects.filter(task_id=task_id):
            alloc.status = ContactAllocationStatus.COMPLETED
            alloc.save()

        # Update task progress calculation
        from apps.contacts.services import update_task_progress
        task_updated = update_task_progress(task_id)
        assert task_updated.status == TaskStatus.COMPLETED

    def test_contact_reassignment(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        contact = Contact.objects.create(first_name="Reassign", phone="9111111111")
        task = Task.objects.create(
            title="Reassign Task", assigned_to=d["emp_a1"], assigned_by=d["manager_a"],
            team=d["team_a"], priority=TaskPriority.MEDIUM, status=TaskStatus.TODO
        )
        alloc = ContactAllocation.objects.create(
            task=task, contact=contact, employee=d["emp_a1"], allocated_by=d["manager_a"]
        )

        # Manager A reassigns to Employee A2
        client_mgr, _, _ = auth_client(d["manager_a"])
        reassign_res = client_mgr.post(f"/api/contacts/allocations/{alloc.id}/reassign/", {
            "new_employee_id": d["emp_a2"].id,
            "reason": "Employee A1 on leave",
        }, format="json")
        assert reassign_res.status_code == 200
        alloc.refresh_from_db()
        assert alloc.employee == d["emp_a2"]

        # Employee cannot reassign -> 403
        client_emp1, _, _ = auth_client(d["emp_a1"].user)
        res_fail = client_emp1.post(f"/api/contacts/allocations/{alloc.id}/reassign/", {
            "new_employee_id": d["emp_a1"].id,
        }, format="json")
        assert res_fail.status_code == 403

    def test_advanced_reports_and_scoping(self, make_user, auth_client):
        d = setup_v2_domain(make_user)
        client_mgr, _, _ = auth_client(d["manager_a"])

        res_emp = client_mgr.get("/api/reports/employee-productivity/")
        assert res_emp.status_code == 200

        res_team = client_mgr.get("/api/reports/team-productivity/")
        assert res_team.status_code == 200

        res_task = client_mgr.get("/api/reports/task-allocations/")
        assert res_task.status_code == 200

        res_contact = client_mgr.get("/api/reports/contact-outcomes/")
        assert res_contact.status_code == 200
