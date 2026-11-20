from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "address", "owner")
    search_fields = ("code", "name")
    fieldsets = (
        ("基本信息", {
            "fields": ("code", "name"),
            "description": "机房编号（唯一）与名称，编号建议如 <code>BJ-DC1</code>。",
        }),
        ("补充信息（可选）", {
            "fields": ("address", "owner"),
            "description": "机房地址与责任人，均可留空。",
        }),
    )
