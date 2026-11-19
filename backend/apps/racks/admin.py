from django.contrib import admin

from .models import Rack


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ("location_code", "name", "room", "total_u",
                    "rated_power_kw", "max_weight_kg")
    list_filter = ("room",)
    search_fields = ("location_code", "name")
