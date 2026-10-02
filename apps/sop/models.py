from django.db import models


class SOPStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    ARCHIVED = "ARCHIVED", "Archived"


def sop_attachment_path(instance, filename):
    return f"sop_attachments/{instance.id or 'temp'}/{filename}"


class SOP(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=100, default="General")
    department = models.ForeignKey(
        "organization.Department", on_delete=models.SET_NULL, null=True, blank=True, related_name="sops"
    )
    process = models.ForeignKey(
        "organization.Process", on_delete=models.SET_NULL, null=True, blank=True, related_name="sops"
    )
    team = models.ForeignKey(
        "organization.Team", on_delete=models.SET_NULL, null=True, blank=True, related_name="sops"
    )
    attachment = models.FileField(upload_to=sop_attachment_path, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SOPStatus.choices, default=SOPStatus.DRAFT)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="created_sops"
    )
    updated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_sops"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["department"]),
            models.Index(fields=["process"]),
            models.Index(fields=["team"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"
