from decimal import Decimal
from apps.racks.models import Rack
from .models import Placement

OCCUPYING = ("active", "reserved")

def get_rack_usage(rack: Rack) -> dict:
    ps = list(Placement.objects.filter(rack=rack, status__in=OCCUPYING))
    used_u = {"A": 0, "B": 0}
    for p in ps:
        used_u[p.face] += p.u_size
    remaining_u = {f: rack.total_u - used_u[f] for f in ("A", "B")}
    active = [p for p in ps if p.status == "active"]
    used_power = sum((p.device.power_w for p in active), Decimal("0"))
    used_weight = sum((p.device.weight_kg for p in active), Decimal("0"))
    rated_w = rack.rated_power_kw * 1000
    if rack.current_load_kw is not None:
        load_ratio = rack.current_load_kw / rack.rated_power_kw
        estimate = False
    else:
        load_ratio = used_power / rated_w if rated_w else Decimal("0")
        estimate = True
    return {
        "used_u_by_face": used_u, "remaining_u_by_face": remaining_u,
        "used_power_w": used_power, "remaining_power_w": rated_w - used_power,
        "used_weight_kg": used_weight, "remaining_weight_kg": rack.max_weight_kg - used_weight,
        "current_load_kw": rack.current_load_kw, "load_ratio": load_ratio,
        "load_ratio_is_estimate": estimate,
    }
