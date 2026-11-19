from django.db import models
from apps.racks.models import Rack
from apps.devices.models import Device

class Placement(models.Model):
    FACE = [("A", "A面"), ("B", "B面")]
    STATUS = [("active", "在架"), ("reserved", "预留"), ("removed", "下架")]
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="placements")
    rack = models.ForeignKey(Rack, on_delete=models.PROTECT, related_name="placements")
    face = models.CharField(max_length=1, choices=FACE)
    start_u = models.PositiveIntegerField()
    u_size = models.PositiveIntegerField()
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS, default="active")
    removed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.rack}/{self.face}/{self.start_u}+{self.u_size}"
