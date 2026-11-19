# backend/apps/placements/tests/test_smoke_e2e.py
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.audit.models import AuditLog

@pytest.mark.django_db
def test_full_lifecycle():
    c = APIClient()
    room = Room.objects.create(code="R1", name="一号")
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    d = Device.objects.create(asset_no="D1", name="D1", power_w=200, weight_kg=20, u_size=2)
    p = c.post("/api/placements/", {"device": d.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    u1 = c.get(f"/api/racks/{rack.id}/usage/").data
    assert u1["used_power_w"] == 200 and u1["used_u_by_face"]["A"] == 2
    c.post(f"/api/placements/{p['id']}/remove/", {}, format="json")
    u2 = c.get(f"/api/racks/{rack.id}/usage/").data
    assert u2["used_power_w"] == 0 and u2["used_u_by_face"]["A"] == 0
    assert AuditLog.objects.exists()
