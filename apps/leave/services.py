from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from common.exceptions import BusinessRuleError
from common.permissions import is_employee_in_actor_scope

from .models import LeaveBalance, LeaveRequest, LeaveStatus, LeaveType


@transaction.atomic
def apply_leave(employee, leave_type_id, start_date, end_date, reason):
    if end_date < start_date:
        raise BusinessRuleError("end_date cannot be earlier than start_date.")

    leave_type = LeaveType.objects.filter(pk=leave_type_id, is_active=True).first()
    if not leave_type:
        raise BusinessRuleError("Leave type not found or inactive.")

    # Check for overlapping pending or approved leave requests
    overlap = LeaveRequest.objects.filter(
        employee=employee,
        status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).exists()
    if overlap:
        raise BusinessRuleError("You already have an active or pending leave request overlapping these dates.")

    year = start_date.year
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={
            "allocated_days": Decimal(str(leave_type.default_days)),
            "used_days": Decimal("0.0"),
            "remaining_days": Decimal(str(leave_type.default_days)),
        },
    )

    total_days = Decimal(str((end_date - start_date).days + 1))
    if balance.remaining_days < total_days:
        raise BusinessRuleError(
            f"Insufficient leave balance. Remaining: {balance.remaining_days} days, Requested: {total_days} days."
        )

    return LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason,
        status=LeaveStatus.PENDING,
    )


@transaction.atomic
def approve_leave(leave_request, approved_by):
    if not is_employee_in_actor_scope(approved_by, leave_request.employee):
        raise BusinessRuleError("You are not authorized to approve leave for this employee.")

    if leave_request.status != LeaveStatus.PENDING:
        raise BusinessRuleError(f"Cannot approve leave request with status {leave_request.status}.")

    year = leave_request.start_date.year
    balance = LeaveBalance.objects.filter(
        employee=leave_request.employee, leave_type=leave_request.leave_type, year=year
    ).first()

    if not balance or balance.remaining_days < leave_request.total_days:
        raise BusinessRuleError("Insufficient leave balance for approval.")

    balance.used_days += leave_request.total_days
    balance.save()

    leave_request.status = LeaveStatus.APPROVED
    leave_request.approved_by = approved_by
    leave_request.approved_at = timezone.now()
    leave_request.save()
    return leave_request


@transaction.atomic
def reject_leave(leave_request, rejected_by, rejection_reason=""):
    if not is_employee_in_actor_scope(rejected_by, leave_request.employee):
        raise BusinessRuleError("You are not authorized to reject leave for this employee.")

    if leave_request.status != LeaveStatus.PENDING:
        raise BusinessRuleError(f"Cannot reject leave request with status {leave_request.status}.")

    leave_request.status = LeaveStatus.REJECTED
    leave_request.approved_by = rejected_by
    leave_request.rejection_reason = rejection_reason
    leave_request.save()
    return leave_request


@transaction.atomic
def cancel_leave(leave_request):
    if leave_request.status in [LeaveStatus.CANCELLED, LeaveStatus.REJECTED]:
        raise BusinessRuleError(f"Leave request is already {leave_request.status.lower()}.")

    if leave_request.status == LeaveStatus.APPROVED:
        year = leave_request.start_date.year
        balance = LeaveBalance.objects.filter(
            employee=leave_request.employee, leave_type=leave_request.leave_type, year=year
        ).first()
        if balance:
            balance.used_days = max(Decimal("0.0"), balance.used_days - leave_request.total_days)
            balance.save()

    leave_request.status = LeaveStatus.CANCELLED
    leave_request.save()
    return leave_request
