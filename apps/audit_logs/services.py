from .models import AuditLog


def log_audit(user, action, model_name="", object_id="", description="", ip_address=None):
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        description=description,
        ip_address=ip_address,
    )
