from django.contrib import admin

from .models import Placement


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ("device", "rack", "face", "start_u", "u_size",
                    "status", "placed_at")
    list_filter = ("status", "face", "rack")
    search_fields = ("device__asset_no", "rack__location_code")
