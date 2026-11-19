import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.devices.models import Device
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.placements.models import Placement


@pytest.mark.django_db
def test_create_device():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-001", "name": "服务器A",
        "type": "server", "power_w": 300, "weight_kg": 15, "u_size": 2}, format="json")
    assert r.status_code == 201, r.content
    assert Device.objects.get(asset_no="AST-001").status == "in_use"


@pytest.mark.django_db
def test_invalid_status_returns_400():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-002", "name": "B",
        "power_w": 1, "weight_kg": 1, "u_size": 1, "status": "unknown"}, format="json")
    assert r.status_code == 400 and "status" in r.data["fields"]


@pytest.mark.django_db
def test_invalid_ip_returns_400():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-003", "name": "C",
        "power_w": 1, "weight_kg": 1, "u_size": 1,
        "ip_addresses": ["not-an-ip"]}, format="json")
    assert r.status_code == 400 and "ip_addresses" in r.data["fields"]


@pytest.mark.django_db
def test_valid_ip_and_octet_passes():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-004", "name": "D",
        "power_w": 1, "weight_kg": 1, "u_size": 1,
        "ip_addresses": ["192.168.1.10"]}, format="json")
    assert r.status_code == 201, r.content
    assert r.data["ip_addresses"] == ["192.168.1.10"]


@pytest.mark.django_db
def test_octet_over_255_returns_400():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-005", "name": "E",
        "power_w": 1, "weight_kg": 1, "u_size": 1,
        "ip_addresses": ["999.1.1.1"]}, format="json")
    assert r.status_code == 400 and "ip_addresses" in r.data["fields"]


@pytest.mark.django_db
def test_duplicate_asset_no_returns_400():
    """UniqueValidator must reject a duplicate asset_no with 400, not a 500 IntegrityError."""
    c = APIClient()
    payload = {"asset_no": "AST-DUP", "name": "Dup",
               "power_w": 1, "weight_kg": 1, "u_size": 1}
    r1 = c.post("/api/devices/", payload, format="json")
    assert r1.status_code == 201, r1.content
    r2 = c.post("/api/devices/", payload, format="json")
    assert r2.status_code == 400, r2.content
    assert "asset_no" in r2.data["fields"]


@pytest.mark.django_db
def test_update_with_own_asset_no_succeeds():
    """A device keeping its own unchanged asset_no must still validate (exclude itself)."""
    c = APIClient()
    payload = {"asset_no": "AST-SAME", "name": "Orig",
               "power_w": 1, "weight_kg": 1, "u_size": 1}
    r1 = c.post("/api/devices/", payload, format="json")
    assert r1.status_code == 201, r1.content
    device_id = r1.data["id"]
    payload["name"] = "改名"
    r2 = c.put(f"/api/devices/{device_id}/", payload, format="json")
    assert r2.status_code == 200, r2.content


# ---- update-time capacity validation (placed devices) ----

def _mk_placed_device():
    room = Room.objects.create(code="R1", name="一号")
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
                               total_u=42, rated_power_kw=Decimal("4.0"),
                               max_weight_kg=Decimal("800"))
    device = Device.objects.create(asset_no="AST-P", name="服务器",
                                   power_w=Decimal("3000"), weight_kg=Decimal("500"), u_size=2)
    Placement.objects.create(device=device, rack=rack, face="A", start_u=1, u_size=2,
                             status="active")
    return device


@pytest.mark.django_db
def test_device_put_raising_power_beyond_rack_budget_returns_400():
    """已上架设备 PUT 把功率抬到机柜预算之上必须 400。"""
    device = _mk_placed_device()
    r = APIClient().put(f"/api/devices/{device.id}/", {
        "asset_no": "AST-P", "name": "服务器", "power_w": "5000",
        "weight_kg": "500", "u_size": 2}, format="json")
    assert r.status_code == 400, r.content
    assert set(r.data.keys()) == {"code", "message", "fields"}


@pytest.mark.django_db
def test_device_put_raising_weight_beyond_rack_limit_returns_400():
    """已上架设备 PUT 把承重抬到机柜上限之上必须 400。"""
    device = _mk_placed_device()
    r = APIClient().put(f"/api/devices/{device.id}/", {
        "asset_no": "AST-P", "name": "服务器", "power_w": "3000",
        "weight_kg": "900", "u_size": 2}, format="json")
    assert r.status_code == 400, r.content


@pytest.mark.django_db
def test_device_put_legal_update_still_200():
    """未超出预算的合法更新（含未上架设备）必须照常 200。"""
    device = _mk_placed_device()
    r = APIClient().put(f"/api/devices/{device.id}/", {
        "asset_no": "AST-P", "name": "服务器-改", "power_w": "2000",
        "weight_kg": "400", "u_size": 2}, format="json")
    assert r.status_code == 200, r.content
    assert r.data["power_w"] == "2000.00"
