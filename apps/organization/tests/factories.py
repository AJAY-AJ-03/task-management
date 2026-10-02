from apps.organization.models import Department, Process, Team


def make_department(name="Customer Support", **extra):
    return Department.objects.create(name=name, **extra)


def make_process(department=None, name="Voice Support", **extra):
    department = department or make_department()
    return Process.objects.create(department=department, name=name, **extra)


def make_team(department=None, process=None, name="Team A", **extra):
    department = department or make_department()
    process = process or make_process(department=department)
    return Team.objects.create(department=department, process=process, name=name, **extra)