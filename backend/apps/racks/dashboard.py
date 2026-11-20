from decimal import Decimal
from apps.placements.services import get_rack_usage
from apps.placements.validation import get_warnings
from .models import Rack

ALERT_RATIO = Decimal("0.9")
WARN_RATIO = Decimal("0.8")


def _rack_status(load_ratio, used_power_w, rack) -> str:
    if load_ratio > ALERT_RATIO or used_power_w > rack.rated_power_kw * 1000:
        return "alert"
    if load_ratio > WARN_RATIO:
        return "warn"
    return "ok"


def dashboard_payload() -> dict:
    racks = list(Rack.objects.select_related("room")
                 .prefetch_related("placements__device").order_by("id"))
    rooms: dict = {}
    load_sum = Decimal("0")
    alert_count = 0
    device_ids: set = set()
    for rack in racks:
        u = get_rack_usage(rack)
        ratio = u["load_ratio"] or Decimal("0")
        load_sum += ratio
        status = _rack_status(ratio, u["used_power_w"], rack)
        if status != "ok":
            alert_count += 1
        for p in rack.placements.all():
            if p.status == "active":
                device_ids.add(p.device_id)
        rooms.setdefault(rack.room_id, {
            "id": rack.room_id, "code": rack.room.code, "name": rack.room.name,
            "racks": [],
        })
        rooms[rack.room_id]["racks"].append({
            "id": rack.id, "location_code": rack.location_code, "name": rack.name,
            "total_u": rack.total_u,
            "used_u": u["used_u_by_face"],
            "load_ratio": ratio, "load_ratio_is_estimate": u["load_ratio_is_estimate"],
            "power": {"used_w": u["used_power_w"],
                      "rated_w": rack.rated_power_kw * 1000},
            "weight": {"used_kg": u["used_weight_kg"], "max_kg": rack.max_weight_kg},
            "warnings": get_warnings(rack),
            "status": status,
        })
    n = len(racks)
    return {
        "summary": {
            "room_count": len(rooms), "rack_count": n,
            "device_count": len(device_ids),
            "avg_load_ratio": (load_sum / n) if n else Decimal("0"),
            "alert_rack_count": alert_count,
        },
        "rooms": list(rooms.values()),
    }
