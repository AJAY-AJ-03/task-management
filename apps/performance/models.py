from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models


class KPITargetType(models.TextChoices):
    NUMBER = "NUMBER", "Number"
    PERCENTAGE = "PERCENTAGE", "Percentage"
    TIME = "TIME", "Time"


class KPI(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, default="Count")
    target_type = models.CharField(
        max_length=20, choices=KPITargetType.choices, default=KPITargetType.NUMBER
    )
    default_target = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return f"{self.name} ({self.unit})"


class EmployeeKPI(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="kpi_targets"
    )
    kpi = models.ForeignKey(KPI, on_delete=models.CASCADE, related_name="employee_targets")
    target = models.DecimalField(max_digits=10, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-effective_from"]
        indexes = [
            models.Index(fields=["employee", "kpi"]),
            models.Index(fields=["effective_from"]),
        ]

    def clean(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError({"effective_to": "effective_to date cannot be earlier than effective_from."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.kpi.name} ({self.target})"


class PerformanceRecord(models.Model):
    employee = models.ForeignKey(
        "employees.EmployeeProfile", on_delete=models.CASCADE, related_name="performance_records"
    )
    kpi = models.ForeignKey(KPI, on_delete=models.PROTECT, related_name="performance_records")
    date = models.DateField()
    target_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    achievement_percentage = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_performance_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "employee"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "kpi", "date"], name="uniq_performance_per_emp_kpi_date")
        ]
        indexes = [
            models.Index(fields=["employee", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["kpi"]),
        ]

    def save(self, *args, **kwargs):
        if self.target_value > Decimal("0.00"):
            self.achievement_percentage = round((self.actual_value / self.target_value) * Decimal("100.00"), 2)
        else:
            self.achievement_percentage = Decimal("0.00")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employee.employee_code} - {self.kpi.name} ({self.date}): {self.achievement_percentage}%"
