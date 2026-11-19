import pytest
from rest_framework.test import APIClient
from apps.devices.models import Device


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
