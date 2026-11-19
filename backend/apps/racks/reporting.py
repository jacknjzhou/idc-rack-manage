import csv
import io

from apps.placements.models import Placement
from apps.placements.services import get_rack_usage
from apps.placements.validation import get_warnings


def usage_payload(rack):
    data = get_rack_usage(rack)
    data["warnings"] = get_warnings(rack)
    return data


def uplan_payload(rack):
    ps = Placement.objects.filter(rack=rack, status__in=("active", "reserved"))
    plan = {"A": [None] * rack.total_u, "B": [None] * rack.total_u}
    for p in ps:
        cell = {"device_id": p.device_id, "asset_no": p.device.asset_no, "status": p.status}
        for u in range(p.start_u, p.start_u + p.u_size):
            if 1 <= u <= rack.total_u:
                plan[p.face][u - 1] = cell
    return plan


def export_devices_csv(rack):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["资产编号", "名称", "型号", "功耗W", "重量kg", "占用U", "面", "起始U"])
    for p in Placement.objects.filter(rack=rack, status="active"):
        d = p.device
        w.writerow([d.asset_no, d.name, d.model, d.power_w, d.weight_kg,
                    p.u_size, p.face, p.start_u])
    return buf.getvalue()
