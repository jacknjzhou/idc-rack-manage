from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement
import pytest


@pytest.mark.django_db
def test_dashboard_payload_and_status_thresholds():
    room = Room.objects.create(code="R1", name="一号机房")
    ok_rack = Rack.objects.create(room=room, name="A01", location_code="R1-A01",
                                  total_u=42, rated_power_kw=Decimal("10"),
                                  max_weight_kg=Decimal("1000"))
    alert_rack = Rack.objects.create(room=room, name="A02", location_code="R1-A02",
                                     total_u=42, rated_power_kw=Decimal("1"),
                                     max_weight_kg=Decimal("1000"))
    d = Device.objects.create(asset_no="D1", name="服务器", power_w=Decimal("900"),
                              weight_kg=Decimal("20"), u_size=2)
    # alert_rack：900W/1000W 额定 → load_ratio 0.9 → alert
    Placement.objects.create(device=d, rack=alert_rack, face="A", start_u=1,
                             u_size=2, status="active")

    u = get_user_model().objects.create_user("op", password="x", role="operator")
    c = APIClient(); c.force_authenticate(u)
    resp = c.get("/api/racks/dashboard/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["room_count"] == 1
    assert body["summary"]["rack_count"] == 2
    assert body["summary"]["device_count"] == 1
    assert body["summary"]["alert_rack_count"] == 1
    assert body["rooms"][0]["code"] == "R1"
    racks = {r["location_code"]: r for r in body["rooms"][0]["racks"]}
    assert racks["R1-A01"]["status"] == "ok"
    assert racks["R1-A02"]["status"] == "alert"
    assert racks["R1-A02"]["used_u"] == {"A": 2, "B": 0}
    assert racks["R1-A02"]["power"]["used_w"] == 900
