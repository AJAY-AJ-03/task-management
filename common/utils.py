from datetime import datetime

from django.utils import timezone


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def local_now():
    return timezone.localtime(timezone.now())


def local_today():
    return local_now().date()


def combine_local(date_value, time_value):
    """Timezone-aware datetime from a date and a time in the project time zone."""
    return timezone.make_aware(datetime.combine(date_value, time_value))


def minutes_between(start, end):
    return max(int((end - start).total_seconds() // 60), 0)