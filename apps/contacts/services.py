import openpyxl
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.employees.models import EmployeeProfile
from apps.tasks.models import Task, TaskPriority, TaskStatus
from apps.tasks.services import log_task_activity
from common.exceptions import BusinessRuleError
from common.permissions import is_employee_in_actor_scope

from .models import (
    Contact,
    ContactAllocation,
    ContactAllocationStatus,
    ContactImport,
)


@transaction.atomic
def parse_and_import_excel(file_obj, uploaded_by):
    if not file_obj.name.endswith(".xlsx"):
        raise BusinessRuleError("Invalid file type. Only .xlsx files are supported.")

    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
    except Exception as e:
        raise BusinessRuleError(f"Failed to parse Excel file: {str(e)}")

    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        raise BusinessRuleError("Excel file is empty.")

    header = [str(cell).strip().lower() if cell is not None else "" for cell in rows[0]]
    required = ["first_name", "phone"]
    for req in required:
        if req not in header:
            raise BusinessRuleError(f"Missing required column in Excel header: '{req}'.")

    fn_idx = header.index("first_name")
    phone_idx = header.index("phone")
    ln_idx = header.index("last_name") if "last_name" in header else -1
    email_idx = header.index("email") if "email" in header else -1
    company_idx = header.index("company") if "company" in header else -1
    notes_idx = header.index("notes") if "notes" in header else -1

    import_log = ContactImport.objects.create(
        file_name=file_obj.name,
        uploaded_by=uploaded_by,
        total_rows=len(rows) - 1,
    )

    contacts_to_create = []
    seen_phones = set()
    validation_errors = []

    for idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue  # skip blank lines

        first_name = str(row[fn_idx]).strip() if fn_idx < len(row) and row[fn_idx] is not None else ""
        phone = str(row[phone_idx]).strip() if phone_idx < len(row) and row[phone_idx] is not None else ""
        last_name = str(row[ln_idx]).strip() if ln_idx != -1 and ln_idx < len(row) and row[ln_idx] is not None else ""
        email = str(row[email_idx]).strip() if email_idx != -1 and email_idx < len(row) and row[email_idx] is not None else ""
        company = str(row[company_idx]).strip() if company_idx != -1 and company_idx < len(row) and row[company_idx] is not None else ""
        notes = str(row[notes_idx]).strip() if notes_idx != -1 and notes_idx < len(row) and row[notes_idx] is not None else ""

        if not first_name:
            validation_errors.append({"row": idx, "error": "first_name is empty."})
            continue
        if not phone:
            validation_errors.append({"row": idx, "error": "phone is empty."})
            continue

        if phone in seen_phones:
            validation_errors.append({"row": idx, "error": f"Duplicate phone '{phone}' in file."})
            continue

        seen_phones.add(phone)
        contacts_to_create.append(
            Contact(
                contact_import=import_log,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                email=email,
                company=company,
                notes=notes,
            )
        )

    if validation_errors and not contacts_to_create:
        import_log.failed_rows = len(validation_errors)
        import_log.validation_errors = validation_errors
        import_log.save()
        raise BusinessRuleError(f"Excel import failed with errors: {validation_errors}")

    created_contacts = Contact.objects.bulk_create(contacts_to_create)
    import_log.success_rows = len(created_contacts)
    import_log.failed_rows = len(validation_errors)
    import_log.validation_errors = validation_errors
    import_log.save()

    return import_log


@transaction.atomic
def allocate_contacts_to_employees(contact_ids, employee_ids, title, deadline=None, notes="", allocated_by=None):
    if not contact_ids:
        raise BusinessRuleError("No contacts selected for allocation.")
    if not employee_ids:
        raise BusinessRuleError("No employees selected for allocation.")

    contacts = list(Contact.objects.filter(id__in=contact_ids))
    if len(contacts) != len(contact_ids):
        raise BusinessRuleError("One or more selected contacts were not found.")

    employees = list(EmployeeProfile.objects.filter(id__in=employee_ids).select_related("team"))
    if len(employees) != len(employee_ids):
        raise BusinessRuleError("One or more selected employees were not found.")

    for emp in employees:
        if not is_employee_in_actor_scope(allocated_by, emp):
            raise BusinessRuleError(f"You are not authorized to allocate contacts to employee {emp.employee_code}.")

    # Create Daily Task
    primary_team = employees[0].team if employees else None
    task = Task.objects.create(
        title=title,
        description=notes,
        assigned_to=employees[0],
        assigned_by=allocated_by,
        team=primary_team,
        priority=TaskPriority.MEDIUM,
        status=TaskStatus.TODO,
        due_date=deadline,
    )

    # Distribute contacts evenly with remainder safe handling
    num_contacts = len(contacts)
    num_employees = len(employees)
    base_chunk = num_contacts // num_employees
    remainder = num_contacts % num_employees

    allocations_to_create = []
    contact_index = 0

    for i, emp in enumerate(employees):
        chunk_count = base_chunk + (1 if i < remainder else 0)
        emp_contacts = contacts[contact_index : contact_index + chunk_count]
        contact_index += chunk_count

        for c in emp_contacts:
            # Deactivate existing active allocations for this contact
            ContactAllocation.objects.filter(contact=c, is_active=True).update(is_active=False)

            allocations_to_create.append(
                ContactAllocation(
                    task=task,
                    contact=c,
                    employee=emp,
                    allocated_by=allocated_by,
                    deadline=deadline,
                    status=ContactAllocationStatus.PENDING,
                    is_active=True,
                )
            )

    ContactAllocation.objects.bulk_create(allocations_to_create)

    log_task_activity(
        task=task,
        actor=allocated_by,
        action="ALLOCATED_CONTACTS",
        new_value=str(num_contacts),
        description=f"Allocated {num_contacts} contacts across {num_employees} employees for daily task '{title}'.",
    )

    update_task_progress(task, actor=allocated_by)
    return task


@transaction.atomic
def update_contact_allocation_status(allocation, new_status, description="", follow_up_date=None, actor=None):
    if new_status not in ContactAllocationStatus.values:
        raise BusinessRuleError("Invalid contact allocation status.")

    old_status = allocation.status
    allocation.status = new_status
    if description:
        allocation.description = description
    if follow_up_date:
        allocation.follow_up_date = follow_up_date
    if actor:
        allocation.updated_by = actor

    allocation.save()

    if old_status != new_status:
        log_task_activity(
            task=allocation.task,
            actor=actor,
            action="CONTACT_STATUS_CHANGED",
            old_value=old_status,
            new_value=new_status,
            description=f"Contact {allocation.contact.phone} status updated from {old_status} to {new_status}.",
        )

    update_task_progress(allocation.task, actor=actor)
    return allocation


@transaction.atomic
def update_task_progress(task, actor=None):
    allocations = task.allocations.filter(is_active=True)
    total = allocations.count()

    if total == 0:
        return task

    completed_outcomes = [
        ContactAllocationStatus.COMPLETED,
        ContactAllocationStatus.NOT_INTERESTED,
        ContactAllocationStatus.FAILED,
        ContactAllocationStatus.CALLBACK,
        ContactAllocationStatus.NO_ANSWER,
    ]
    completed = allocations.filter(status__in=completed_outcomes).count()
    terminal_done = allocations.filter(
        status__in=[ContactAllocationStatus.COMPLETED, ContactAllocationStatus.NOT_INTERESTED, ContactAllocationStatus.FAILED]
    ).count()

    old_status = task.status
    if completed == 0:
        new_status = TaskStatus.TODO
    elif completed == total or terminal_done == total:
        new_status = TaskStatus.COMPLETED
    else:
        new_status = TaskStatus.PARTIALLY_COMPLETED if terminal_done > 0 else TaskStatus.IN_PROGRESS

    if old_status != new_status:
        task.status = new_status
        task.save()
        log_task_activity(
            task=task,
            actor=actor,
            action="PROGRESS_STATUS_UPDATED",
            old_value=old_status,
            new_value=new_status,
            description=f"Overall task status updated to {new_status} ({completed}/{total} contacts processed).",
        )

    return task


@transaction.atomic
def reassign_contact_allocation(allocation, new_employee_id, actor, reason=""):
    new_emp = EmployeeProfile.objects.filter(pk=new_employee_id).first()
    if not new_emp:
        raise BusinessRuleError("Target employee profile for reassignment not found.")

    if not is_employee_in_actor_scope(actor, new_emp):
        raise BusinessRuleError("You are not authorized to assign contacts to this employee.")

    prev_emp_code = allocation.employee.employee_code

    allocation.is_active = False
    allocation.save()

    new_allocation = ContactAllocation.objects.create(
        task=allocation.task,
        contact=allocation.contact,
        employee=new_emp,
        allocated_by=actor,
        deadline=allocation.deadline,
        status=ContactAllocationStatus.PENDING,
        description=f"Reassigned from {prev_emp_code}. Reason: {reason}".strip(),
        is_active=True,
    )

    log_task_activity(
        task=allocation.task,
        actor=actor,
        action="CONTACT_REASSIGNED",
        old_value=prev_emp_code,
        new_value=new_emp.employee_code,
        description=f"Contact {allocation.contact.phone} reassigned from {prev_emp_code} to {new_emp.employee_code}. {reason}".strip(),
    )

    update_task_progress(allocation.task, actor=actor)
    return new_allocation
