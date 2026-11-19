from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from apps.rooms.models import Room
from .models import Rack


class RackRequestSerializer(serializers.Serializer):
    """Rack 请求 Schema：类型/必填/正则/唯一性校验由 DRF 自动执行。"""
    room = serializers.PrimaryKeyRelatedField(queryset=Room.objects.all())
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    location_code = serializers.RegexField(
        r"^[A-Za-z0-9_-]+$", max_length=64,
        validators=[UniqueValidator(queryset=Rack.objects.all())],
        error_messages={"invalid": "机位编码只能含字母、数字、下划线、连字符"},
    )
    location_desc = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    total_u = serializers.IntegerField(min_value=1, max_value=100)
    rated_power_kw = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.01)
    max_weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    current_load_kw = serializers.DecimalField(
        max_digits=8, decimal_places=2,
        min_value=0, required=False, allow_null=True, default=None,
    )
    metrics_endpoint = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class RackResponseSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)

    class Meta:
        model = Rack
        fields = ["id", "room", "room_name", "name", "location_code", "location_desc",
                  "total_u", "rated_power_kw", "max_weight_kg", "current_load_kw", "metrics_endpoint"]
        read_only_fields = fields
