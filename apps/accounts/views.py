from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from common.responses import ErrorEnvelopeSerializer, envelope, success_response

from . import services
from .serializers import (
    ChangePasswordSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    TokenRefreshRequestSerializer,
    TokenRefreshResponseSerializer,
    UserSerializer,
)

ERRORS = {400: ErrorEnvelopeSerializer, 401: ErrorEnvelopeSerializer}


class PublicAPIView(APIView):
    """Unauthenticated endpoint that still reports auth failures as 401, not 403."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'


class LoginView(PublicAPIView):
    @extend_schema(
        summary="Log in",
        description="Authenticate with username and password. Returns JWT access/refresh tokens and a brief user profile. Throttled.",
        request=LoginSerializer,
        responses={
            200: envelope("LoginEnvelope", LoginResponseSerializer()),
            **ERRORS,
            429: ErrorEnvelopeSerializer,
        },
        auth=[],
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        return success_response(serializer.validated_data, "Login successful.")


class RefreshView(PublicAPIView):
    @extend_schema(
        summary="Refresh access token",
        description="Exchange a valid refresh token for a new access token. Refresh tokens rotate; the old one is blacklisted.",
        request=TokenRefreshRequestSerializer,
        responses={200: envelope("RefreshEnvelope", TokenRefreshResponseSerializer()), **ERRORS},
        auth=[],
        tags=["Auth"],
    )
    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        return success_response(serializer.validated_data, "Token refreshed successfully.")


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Log out",
        description="Blacklists the supplied refresh token so it can no longer be used.",
        request=LogoutSerializer,
        responses={200: envelope("LogoutEnvelope"), **ERRORS},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.logout_user(request.user, serializer.validated_data["refresh"])
        return success_response(message="Logged out successfully.")


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Current user",
        description="Returns the authenticated user's account details.",
        responses={200: envelope("MeEnvelope", UserSerializer()), 401: ErrorEnvelopeSerializer},
        tags=["Auth"],
    )
    def get(self, request):
        return success_response(
            UserSerializer(request.user).data, "Profile retrieved successfully."
        )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(
        summary="Change password",
        description="Requires the current password. All existing refresh tokens are revoked, so the user must log in again.",
        request=ChangePasswordSerializer,
        responses={200: envelope("ChangePasswordEnvelope"), **ERRORS},
        tags=["Auth"],
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(
            request.user,
            serializer.validated_data["old_password"],
            serializer.validated_data["new_password"],
        )
        return success_response(message="Password changed successfully. Please log in again.")