from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models


class LeaveStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_days = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="leave_balances"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveIntegerField()
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("12.0"))
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    remaining_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("12.0"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "leave_type"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "leave_type", "year"], name="uniq_leave_balance_per_year")
        ]
        indexes = [
            models.Index(fields=["employee", "year"]),
        ]

    def save(self, *args, **kwargs):
        self.remaining_days = self.allocated_days - self.used_days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.name} ({self.year}): {self.remaining_days} remaining"


class LeaveRequest(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("1.0"))
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_leave_requests"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["status"]),
        ]

    def clean(self):
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "end_date cannot be earlier than start_date."})

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date:
            diff = (self.end_date - self.start_date).days + 1
            self.total_days = Decimal(str(diff))
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.leave_type.name} ({self.start_date} to {self.end_date}): {self.status}"
