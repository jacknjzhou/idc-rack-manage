from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.racks.models import Rack
from .models import Placement
from .services import get_rack_usage

LOAD_WARN_RATIO = Decimal("0.8")
_OCCUPYING = ("active", "reserved")

def validate_placement(rack, face, start_u, u_size, power_w, weight_kg, exclude_id=None) -> None:
    qs = Placement.objects.filter(rack=rack, face=face, status__in=_OCCUPYING)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    for p in qs:
        if start_u <= p.start_u + p.u_size - 1 and p.start_u <= start_u + u_size - 1:
            raise ValidationError("U位冲突：该面指定U位已被占用")
    if start_u < 1 or start_u + u_size - 1 > rack.total_u:
        raise ValidationError("超出总U数范围")
    u = get_rack_usage(rack)
    if u["used_power_w"] + Decimal(power_w) > rack.rated_power_kw * 1000:
        raise ValidationError("功率超出机柜额定功率")
    if u["used_weight_kg"] + Decimal(weight_kg) > rack.max_weight_kg:
        raise ValidationError("承重超出机柜上限")

def validate_rack_update(rack, total_u, rated_power_kw, max_weight_kg) -> None:
    """机柜更新时校验新容量不低于当前用量（closed-interval U，双面取最大）。"""
    u = get_rack_usage(rack)
    used_u = max(u["used_u_by_face"].values())
    if total_u < used_u:
        raise ValidationError(f"total_u 不能低于当前已用 U 数（{used_u}U）")
    if Decimal(rated_power_kw) * 1000 < u["used_power_w"]:
        raise ValidationError("额定功率不能低于当前已用功率")
    if Decimal(max_weight_kg) < u["used_weight_kg"]:
        raise ValidationError("承重上限不能低于当前已用承重")


def _rack_usage_excluding_device(rack, device) -> dict:
    """该机柜的用量，但排除指定设备的放置记录（功率/承重只算 active）。"""
    ps = list(Placement.objects.filter(rack=rack, status__in=_OCCUPYING)
              .exclude(device=device))
    used_power = sum((p.device.power_w for p in ps if p.status == "active"), Decimal("0"))
    used_weight = sum((p.device.weight_kg for p in ps if p.status == "active"), Decimal("0"))
    return {"used_power_w": used_power, "used_weight_kg": used_weight}


def validate_device_update(device, power_w, weight_kg) -> None:
    """设备更新时校验每个 ACTIVE 放置：扣除自身后，新功率/承重仍须 fits 机柜预算。"""
    for p in Placement.objects.filter(device=device, status="active"):
        other = _rack_usage_excluding_device(p.rack, device)
        if other["used_power_w"] + Decimal(power_w) > p.rack.rated_power_kw * 1000:
            raise ValidationError(f"功率超出机柜 {p.rack} 的额定功率")
        if other["used_weight_kg"] + Decimal(weight_kg) > p.rack.max_weight_kg:
            raise ValidationError(f"承重超出机柜 {p.rack} 的上限")


def get_warnings(rack: Rack) -> list:
    u = get_rack_usage(rack)
    warns = []
    if u["load_ratio"] is not None and u["load_ratio"] > LOAD_WARN_RATIO:
        suffix = "（估算）" if u["load_ratio_is_estimate"] else ""
        warns.append(f"负载率 {u['load_ratio']:.0%} 超过告警阈值 80%{suffix}")
    return warns
