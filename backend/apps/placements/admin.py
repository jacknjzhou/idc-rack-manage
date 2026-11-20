from django.contrib import admin

from .models import Placement


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ("device", "rack", "face", "start_u", "u_size",
                    "status", "placed_at")
    list_filter = ("status", "face", "rack")
    search_fields = ("device__asset_no", "rack__location_code")
    autocomplete_fields = ("device", "rack")  # 依赖设备表与机柜表：搜索式下拉
    fieldsets = (
        ("放置对象（先建设备与机柜）", {
            "fields": ("device", "rack"),
            "description": "把哪台设备放进哪个机柜。两张表都由搜索下拉选择"
                           "（输入资产编号 / 位置编号过滤）；PROTECT：已放置的设备与机柜不可删除。",
        }),
        ("位置", {
            "fields": ("face", "start_u", "u_size"),
            "description": "face：A 面（前）/ B 面（后）；start_u 起始 U 位从 1 计，"
                           "U 位图按从下往上编号；u_size 通常应等于设备档案里的 u_size。"
                           "保存时校验：同面 U 位不重叠、不超机柜总 U 数、"
                           "功率与承重不超机柜预算。",
        }),
        ("状态", {
            "fields": ("status", "placed_at", "removed_at"),
            "description": "active 在架 / reserved 预留（预留也占 U 位但不算功率承重）/ "
                           "removed 下架。下架请用 API 的 <code>POST /api/placements/{id}/remove/</code>，"
                           "它会自动写 removed_at；此处手工改状态不会补时间。",
        }),
    )
