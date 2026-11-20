from rest_framework import serializers


class UsageResponseSerializer(serializers.Serializer):
    used_u_by_face = serializers.DictField(child=serializers.IntegerField())
    remaining_u_by_face = serializers.DictField(child=serializers.IntegerField())
    used_power_w = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_power_w = serializers.DecimalField(max_digits=12, decimal_places=2)
    used_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_load_kw = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    load_ratio = serializers.DecimalField(max_digits=8, decimal_places=4, allow_null=True)
    load_ratio_is_estimate = serializers.BooleanField()
    warnings = serializers.ListField(child=serializers.CharField())


class UPlanCellSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    asset_no = serializers.CharField()
    status = serializers.CharField()


class UPlanResponseSerializer(serializers.Serializer):
    A = serializers.ListField(child=UPlanCellSerializer(), allow_null=True)
    B = serializers.ListField(child=UPlanCellSerializer(), allow_null=True)


class RackDashSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    location_code = serializers.CharField()
    name = serializers.CharField()
    total_u = serializers.IntegerField()
    used_u = serializers.DictField(child=serializers.IntegerField())
    load_ratio = serializers.FloatField()
    load_ratio_is_estimate = serializers.BooleanField()
    power = serializers.DictField(child=serializers.FloatField())
    weight = serializers.DictField(child=serializers.FloatField())
    warnings = serializers.ListField(child=serializers.CharField())
    status = serializers.ChoiceField(choices=["ok", "warn", "alert"])


class RoomDashSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    racks = RackDashSerializer(many=True)


class DashboardResponseSerializer(serializers.Serializer):
    summary = serializers.DictField(child=serializers.JSONField())
    rooms = RoomDashSerializer(many=True)
