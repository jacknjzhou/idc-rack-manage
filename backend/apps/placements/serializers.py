from rest_framework import serializers
from apps.devices.models import Device
from apps.racks.models import Rack
from .models import Placement

class PlaceRequestSerializer(serializers.Serializer):
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.all())
    face = serializers.ChoiceField(choices=["A", "B"])
    start_u = serializers.IntegerField(min_value=1)
    u_size = serializers.IntegerField(min_value=1, max_value=10)

class MoveRequestSerializer(serializers.Serializer):
    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.all())
    face = serializers.ChoiceField(choices=["A", "B"])
    start_u = serializers.IntegerField(min_value=1)

class PlacementResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Placement
        fields = ["id", "device", "rack", "face", "start_u", "u_size",
                  "placed_at", "status", "removed_at"]
        read_only_fields = fields
