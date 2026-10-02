from django.core.exceptions import ValidationError
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.name


class Process(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="processes")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["department__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="uniq_process_per_department")
        ]
        indexes = [models.Index(fields=["department", "is_active"])]

    def __str__(self):
        return f"{self.department.name} / {self.name}"


class Team(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="teams")
    process = models.ForeignKey(Process, on_delete=models.PROTECT, related_name="teams")
    manager = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_teams"
    )
    team_leader = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="led_teams"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "process", "name"], name="uniq_team_per_process")
        ]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["process"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        if self.process_id and self.department_id and self.process.department_id != self.department_id:
            raise ValidationError({"process": "Process must belong to the selected department."})

    def __str__(self):
        return self.name