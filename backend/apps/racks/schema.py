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
