from rest_framework import serializers

from .models import AuditLog


class AuditLogResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "operator", "action", "target", "before", "after", "created_at"]
        read_only_fields = fields
