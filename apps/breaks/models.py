from django.core.exceptions import ValidationError
from django.db import models


class BreakStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class BreakType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    is_paid = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return f"{self.name} ({self.duration_minutes}m)"


class BreakRecord(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="break_records"
    )
    break_type = models.ForeignKey(BreakType, on_delete=models.PROTECT, related_name="records")
    attendance = models.ForeignKey(
        "attendance.Attendance", on_delete=models.SET_NULL, null=True, blank=True, related_name="breaks"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=BreakStatus.choices, default=BreakStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["employee", "status"]),
            models.Index(fields=["start_time"]),
            models.Index(fields=["status"]),
        ]

    def clean(self):
        if self.end_time and self.end_time < self.start_time:
            raise ValidationError({"end_time": "end_time cannot be earlier than start_time."})

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            diff = self.end_time - self.start_time
            self.duration_seconds = max(0, int(diff.total_seconds()))
            if self.status == BreakStatus.ACTIVE:
                self.status = BreakStatus.COMPLETED
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.break_type.name} ({self.status})"
