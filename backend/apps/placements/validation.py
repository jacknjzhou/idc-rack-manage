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
    if start_u < 1 or start_u + u_size > rack.total_u:
        raise ValidationError("超出总U数范围")
    u = get_rack_usage(rack)
    if u["used_power_w"] + Decimal(power_w) > rack.rated_power_kw * 1000:
        raise ValidationError("功率超出机柜额定功率")
    if u["used_weight_kg"] + Decimal(weight_kg) > rack.max_weight_kg:
        raise ValidationError("承重超出机柜上限")

def get_warnings(rack: Rack) -> list:
    u = get_rack_usage(rack)
    warns = []
    if u["load_ratio"] is not None and u["load_ratio"] > LOAD_WARN_RATIO:
        suffix = "（估算）" if u["load_ratio_is_estimate"] else ""
        warns.append(f"负载率 {u['load_ratio']:.0%} 超过告警阈值 80%{suffix}")
    return warns
