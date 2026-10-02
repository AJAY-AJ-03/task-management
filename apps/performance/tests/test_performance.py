from decimal import Decimal
import pytest

from apps.accounts.models import User
from apps.organization.tests.factories import make_department, make_process, make_team
from apps.performance.models import KPI, PerformanceRecord
from apps.performance.services import calculate_achievement, record_daily_performance


@pytest.mark.django_db
def test_achievement_calculation_formula():
    assert calculate_achievement(100, 85) == Decimal("85.00")
    assert calculate_achievement(50, 50) == Decimal("100.00")
    assert calculate_achievement(0, 50) == Decimal("0.00")  # zero division safe


@pytest.mark.django_db
def test_kpi_and_performance_record_flow(auth_client, make_user):
    admin = make_user("prf_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    dept = make_department("Perf Dept")
    proc = make_process(dept, "Perf Proc")
    team = make_team(dept, proc, "Perf Team")

    emp_payload = {
        "username": "prf_emp",
        "email": "prf_emp@example.com",
        "password": "Password123!",
        "first_name": "Perf",
        "last_name": "Worker",
        "role": "EMPLOYEE",
        "employee_code": "EMP_PRF1",
        "date_of_joining": "2026-01-01",
        "designation": "CSR",
        "department": dept.id,
        "process": proc.id,
        "team": team.id,
        "phone": "9876543210",
        "status": "ACTIVE",
    }
    api_admin.post("/api/employees/", emp_payload)
    emp_user = User.objects.get(username="prf_emp")

    # Create KPI
    kpi_res = api_admin.post(
        "/api/kpis/",
        {
            "name": "Calls Handled",
            "unit": "Calls",
            "target_type": "NUMBER",
            "default_target": "50.00",
        },
    )
    assert kpi_res.status_code == 201
    kpi_id = kpi_res.data["data"]["id"]

    # Record daily performance as Manager/TL
    perf_res = api_admin.post(
        "/api/performance/",
        {
            "employee": emp_user.employee_profile.id,
            "kpi": kpi_id,
            "date": "2026-10-01",
            "target_value": "50.00",
            "actual_value": "45.00",
        },
    )
    assert perf_res.status_code == 201
    assert perf_res.data["data"]["achievement_percentage"] == "90.00"

    # Employee views my performance
    api_emp, _, _ = auth_client(emp_user, password="Password123!")
    my_perf = api_emp.get("/api/performance/my/")
    assert my_perf.status_code == 200
    assert len(my_perf.data["data"]) == 1
