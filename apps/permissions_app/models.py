import datetime
from django.core.exceptions import ValidationError
from django.db import models


class PermissionStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class PermissionRequest(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="permission_requests"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=0)
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=PermissionStatus.choices, default=PermissionStatus.PENDING
    )
    approved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_permission_requests"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-start_time"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["date"]),
            models.Index(fields=["status"]),
        ]

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({"end_time": "end_time must be later than start_time."})

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            dummy_date = datetime.date(2000, 1, 1)
            st = datetime.datetime.combine(dummy_date, self.start_time)
            et = datetime.datetime.combine(dummy_date, self.end_time)
            diff = et - st
            self.duration_minutes = int(diff.total_seconds() // 60)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.date} ({self.start_time}-{self.end_time}): {self.status}"
