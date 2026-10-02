import pytest


@pytest.mark.django_db
def test_attendance_report_json_and_csv_export(auth_client, make_user):
    admin = make_user("rpt_admin", role="SUPER_ADMIN")
    api_admin, _, _ = auth_client(admin)

    # JSON export
    res_json = api_admin.get("/api/reports/attendance/?format=json")
    assert res_json.status_code == 200
    assert isinstance(res_json.data["data"], list)

    # CSV export
    res_csv = api_admin.get("/api/reports/attendance/?format=csv")
    assert res_csv.status_code == 200
    assert res_csv.headers["Content-Type"] == "text/csv"
    assert "attachment; filename=" in res_csv.headers["Content-Disposition"]

    # Excel export
    res_excel = api_admin.get("/api/reports/attendance/?format=excel")
    assert res_excel.status_code == 200
    assert "openxmlformats-officedocument" in res_excel.headers["Content-Type"]
