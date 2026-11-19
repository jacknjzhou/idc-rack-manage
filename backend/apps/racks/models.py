from django.db import models
from apps.rooms.models import Room


class Rack(models.Model):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="racks")
    name = models.CharField(max_length=128)
    location_code = models.CharField(max_length=64, unique=True)
    location_desc = models.CharField(max_length=255, blank=True)
    total_u = models.PositiveIntegerField()
    rated_power_kw = models.DecimalField(max_digits=8, decimal_places=2)
    max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    current_load_kw = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    metrics_endpoint = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.location_code
