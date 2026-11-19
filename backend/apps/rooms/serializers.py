from rest_framework import serializers
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Room

class RoomRequestSerializer(serializers.Serializer):
    """Room 请求 Schema：类型/必填/正则校验由 DRF 自动执行。"""
    code = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=64,
                                  error_messages={"invalid": "位置编码只能含字母、数字、下划线、连字符"})
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    owner = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")

class RoomResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "code", "name", "address", "owner"]
        read_only_fields = fields
