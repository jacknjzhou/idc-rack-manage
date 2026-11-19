from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import AuditLog
from .serializers import AuditLogResponseSerializer


@extend_schema_view(
    list=extend_schema(responses={200: AuditLogResponseSerializer(many=True)}, tags=["审计"]),
    retrieve=extend_schema(responses={200: AuditLogResponseSerializer}, tags=["审计"]),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by("-created_at")
    serializer_class = AuditLogResponseSerializer
