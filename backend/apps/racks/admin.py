from django.contrib import admin

from .models import Rack


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    list_display = ("location_code", "name", "room", "total_u",
                    "rated_power_kw", "max_weight_kg")
    list_filter = ("room",)
    search_fields = ("location_code", "name")
    autocomplete_fields = ("room",)  # 依赖机房表：搜索式下拉选择
    fieldsets = (
        ("所属机房（先建机房，再建机柜）", {
            "fields": ("room",),
            "description": "机柜必须挂在某个机房下；<code>on_delete=PROTECT</code> "
                           "——机房下还有机柜时不允许删除机房。",
        }),
        ("标识", {
            "fields": ("name", "location_code", "location_desc"),
            "description": "位置编号全局唯一（如 <code>BJ-DC1-A01</code>），"
                           "是列表页与 API 引用机柜的主标识。",
        }),
        ("容量参数（U 位图与告警都依赖这三项）", {
            "fields": ("total_u", "rated_power_kw", "max_weight_kg"),
            "description": "总 U 数（如 42U）；额定功率 kW 与承重 kg 是上架校验的预算上限；"
                           "修改时不能低于当前已用量。",
        }),
        ("监控（可选）", {
            "fields": ("current_load_kw", "metrics_endpoint"),
            "description": "实际电表功率（kW，可空，为空时负载率按设备功率估算）；"
                           "metrics_endpoint 填 PDU/动环监控地址。",
        }),
    )
