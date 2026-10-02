import pytest

from apps.organization.tests.factories import make_department, make_process, make_team


@pytest.fixture
def org_setup(db):
    department = make_department()
    process = make_process(department)
    team = make_team(department, process)
    return department, process, team