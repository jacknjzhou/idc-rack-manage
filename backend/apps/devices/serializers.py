import re

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Device


class IPField(serializers.CharField):
    """简单 IPv4 正则校验。"""
    def __init__(self, **kwargs):
        kwargs.setdefault("validators", [])
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        v = super().to_internal_value(data)
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", v) or any(int(x) > 255 for x in v.split(".")):
            raise serializers.ValidationError("非法 IP 地址")
        return v


class DeviceRequestSerializer(serializers.Serializer):
    asset_no = serializers.RegexField(
        r"^[A-Za-z0-9_-]+$", max_length=64,
        validators=[UniqueValidator(queryset=Device.objects.all())],
    )
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    model = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    power_w = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    u_size = serializers.IntegerField(min_value=1, max_value=10)
    ip_addresses = serializers.ListField(child=IPField(), required=False, default=list)
    purchase_date = serializers.DateField(required=False, allow_null=True, default=None)
    warranty_end = serializers.DateField(required=False, allow_null=True, default=None)
    status = serializers.ChoiceField(choices=["in_use", "warranty", "retired"], default="in_use")


class DeviceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "asset_no", "name", "type", "model", "power_w", "weight_kg",
                  "u_size", "ip_addresses", "purchase_date", "warranty_end", "status"]
        read_only_fields = fields
