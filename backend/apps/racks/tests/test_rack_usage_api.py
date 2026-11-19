import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement

@pytest.fixture
def rack():
    room = Room.objects.create(code="R1", name="一号")
    return Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=5, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"),
        current_load_kw=Decimal("0.9"))

@pytest.mark.django_db
def test_usage_endpoint(rack):
    r = APIClient().get(f"/api/racks/{rack.id}/usage/")
    assert r.status_code == 200
    assert r.data["remaining_u_by_face"] == {"A": 5, "B": 5}
    assert any("负载率" in x for x in r.data["warnings"])

@pytest.mark.django_db
def test_uplan_endpoint(rack):
    d = Device.objects.create(asset_no="D1", name="D1", power_w=100, weight_kg=10, u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=2, u_size=2)
    r = APIClient().get(f"/api/racks/{rack.id}/uplan/")
    assert len(r.data["A"]) == 5
    assert r.data["A"][0] is None and r.data["A"][1]["asset_no"] == "D1"

@pytest.mark.django_db
def test_export_devices_csv(rack):
    d = Device.objects.create(asset_no="D1", name="服务器A", power_w=100, weight_kg=10, u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=1, u_size=2)
    r = APIClient().get(f"/api/racks/{rack.id}/export_devices/")
    assert r.status_code == 200 and "D1" in r.content.decode()
    assert r["Content-Type"].startswith("text/csv")

@pytest.mark.django_db
def test_rack_actions_in_openapi_schema():
    paths = APIClient().get("/api/schema/").data["paths"]
    assert any("usage" in p for p in paths)
    assert any("uplan" in p for p in paths)
    assert any("export_devices" in p for p in paths)
