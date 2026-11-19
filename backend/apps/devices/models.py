from django.db import models


class Device(models.Model):
    STATUS = [("in_use", "在用"), ("warranty", "维保"), ("retired", "报废")]
    asset_no = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=128, blank=True)
    power_w = models.DecimalField(max_digits=10, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    u_size = models.PositiveIntegerField()
    ip_addresses = models.JSONField(default=list, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="in_use")

    def __str__(self):
        return f"{self.asset_no} {self.name}"
