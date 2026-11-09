from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    responses=inline_serializer(
        "Health",
        {
            "status": serializers.CharField(),
            "database": serializers.CharField(),
            "database_engine": serializers.CharField(),
        },
    )
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Lightweight health check: confirms the API and the database respond."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:  # pragma: no cover - only hit when the DB is down
        db_ok = False

    status_code = 200 if db_ok else 503
    return Response(
        {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "unavailable",
            "database_engine": connection.vendor,
        },
        status=status_code,
    )
