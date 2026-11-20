from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("asset_no", "name", "model", "u_size",
                    "power_w", "weight_kg", "status")
    list_filter = ("status",)
    search_fields = ("asset_no", "name")
    fieldsets = (
        ("资产标识", {
            "fields": ("asset_no", "name"),
            "description": "资产编号全局唯一（如 <code>SRV-2024-001</code>）；"
                           "名称是设备用途描述（如 <code>业务服务器-01</code>）。",
        }),
        ("规格（上架校验的依据）", {
            "fields": ("type", "model", "u_size", "power_w", "weight_kg"),
            "description": "type 填设备类别（如 服务器/交换机/存储）；"
                           "u_size 是设备高度（1U=44.45mm，1U/2U/4U…）；"
                           "power_w 与 weight_kg 用于机柜功率/承重预算校验，"
                           "必填——上架时按这两个数扣减机柜余量。",
        }),
        ("网络（可选）", {
            "fields": ("ip_addresses",),
            "description": "JSON 数组，如 <code>[\"10.0.1.10\", \"10.0.2.10\"]</code>；"
                           "一行一个由前端展示，此处可粘贴 JSON。",
        }),
        ("生命周期", {
            "fields": ("status", "purchase_date", "warranty_end"),
            "description": "status：在用/维保/报废；采购与维保到期日可空。",
        }),
    )
