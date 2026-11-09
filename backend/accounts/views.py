from django.contrib.auth import login, logout, update_session_auth_hash
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SessionPayloadSerializer,
    UserSerializer,
)


def session_payload(request):
    if request.user.is_authenticated:
        return {"authenticated": True, "user": UserSerializer(request.user).data}
    return {"authenticated": False, "user": None}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(APIView):
    """
    GET /api/auth/session/

    Called once when the React app starts. It tells the app whether the user
    is logged in, and guarantees the browser has a `csrftoken` cookie that
    the app must send back in the `X-CSRFToken` header on every write request.
    """

    permission_classes = [AllowAny]

    @extend_schema(responses=SessionPayloadSerializer)
    def get(self, request):
        return Response(session_payload(request))


# DRF only enforces CSRF for already-authenticated sessions. Login and
# register are used by anonymous users, so we enforce CSRF explicitly to
# block "login CSRF" attacks.
@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    """POST /api/auth/register/ — create an account and sign in immediately."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={201: SessionPayloadSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response(session_payload(request), status=status.HTTP_201_CREATED)


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """POST /api/auth/login/ — start a session (sets an HttpOnly session cookie)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginSerializer, responses=SessionPayloadSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return Response(session_payload(request))


class LogoutView(APIView):
    """POST /api/auth/logout/ — end the session."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    """PATCH /api/auth/profile/ {display_name} — returns the updated user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=ProfileSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """
    POST /api/auth/password/ {current_password, new_password, new_password_confirm}

    Changing the password logs out every OTHER session of this user (e.g. a
    forgotten login on another computer); this browser stays logged in.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password"

    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        update_session_auth_hash(request, request.user)  # keep THIS session valid
        return Response(status=status.HTTP_204_NO_CONTENT)
