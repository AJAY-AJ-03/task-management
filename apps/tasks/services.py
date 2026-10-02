from django.db import transaction

from apps.employees.models import EmployeeProfile
from common.exceptions import BusinessRuleError
from common.permissions import is_employee_in_actor_scope

from .models import Task, TaskActivity, TaskStatus


def log_task_activity(task, actor, action, old_value="", new_value="", description="", metadata=None):
    return TaskActivity.objects.create(
        task=task,
        actor=actor,
        action=action,
        old_value=str(old_value or ""),
        new_value=str(new_value or ""),
        description=description,
        metadata=metadata or {},
    )


@transaction.atomic
def create_task(assigned_by, assigned_to_id, title, description="", priority="MEDIUM", due_date=None, team_id=None):
    assigned_to = EmployeeProfile.objects.filter(pk=assigned_to_id).first()
    if not assigned_to:
        raise BusinessRuleError("Assigned employee profile not found.")

    if not is_employee_in_actor_scope(assigned_by, assigned_to):
        raise BusinessRuleError("You are not authorized to assign tasks to this employee.")

    team = assigned_to.team
    if team_id:
        from apps.organization.models import Team
        team = Team.objects.filter(pk=team_id).first() or team

    task = Task.objects.create(
        title=title,
        description=description,
        assigned_to=assigned_to,
        assigned_by=assigned_by,
        team=team,
        priority=priority,
        status=TaskStatus.TODO,
        due_date=due_date,
    )
    log_task_activity(
        task=task,
        actor=assigned_by,
        action="CREATED",
        new_value=task.title,
        description=f"Task '{task.title}' created and assigned to {assigned_to.employee_code}.",
    )
    return task


@transaction.atomic
def update_task_status(task, new_status, actor=None):
    if new_status not in TaskStatus.values:
        raise BusinessRuleError("Invalid task status.")

    old_status = task.status
    task.status = new_status
    task.save()

    if old_status != new_status:
        log_task_activity(
            task=task,
            actor=actor,
            action="STATUS_CHANGED",
            old_value=old_status,
            new_value=new_status,
            description=f"Task status changed from {old_status} to {new_status}.",
        )
    return task


@transaction.atomic
def reassign_task(task, new_assigned_to_id, reassigned_by):
    new_emp = EmployeeProfile.objects.filter(pk=new_assigned_to_id).first()
    if not new_emp:
        raise BusinessRuleError("New assigned employee profile not found.")

    if not is_employee_in_actor_scope(reassigned_by, new_emp):
        raise BusinessRuleError("You are not authorized to assign tasks to this employee.")

    old_emp_code = task.assigned_to.employee_code if task.assigned_to else ""
    task.assigned_to = new_emp
    task.team = new_emp.team
    task.assigned_by = reassigned_by
    task.save()

    log_task_activity(
        task=task,
        actor=reassigned_by,
        action="REASSIGNED",
        old_value=old_emp_code,
        new_value=new_emp.employee_code,
        description=f"Task reassigned from {old_emp_code} to {new_emp.employee_code}.",
    )
    return task
