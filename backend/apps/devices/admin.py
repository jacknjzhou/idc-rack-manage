from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("asset_no", "name", "model", "u_size",
                    "power_w", "weight_kg", "status")
    list_filter = ("status",)
    search_fields = ("asset_no", "name")
