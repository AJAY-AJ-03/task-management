from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from common.exceptions import BusinessRuleError


def revoke_all_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=t) for t in tokens.exclude(blacklistedtoken__isnull=False)],
        ignore_conflicts=True,
    )


def logout_user(user, refresh_token):
    try:
        token = RefreshToken(refresh_token)
    except TokenError:
        raise BusinessRuleError("Invalid or expired refresh token.")
    if str(token.get("user_id")) != str(user.pk):
        raise BusinessRuleError("Invalid or expired refresh token.")
    try:
        token.blacklist()
    except TokenError:
        raise BusinessRuleError("Invalid or expired refresh token.")


@transaction.atomic
def change_password(user, old_password, new_password):
    if not user.check_password(old_password):
        raise BusinessRuleError("Current password is incorrect.")
    if old_password == new_password:
        raise BusinessRuleError("New password must be different from the current one.")
    validate_password(new_password, user=user)
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    revoke_all_tokens(user)  # force re-login on all devices