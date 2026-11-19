import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement


@pytest.fixture
def room(db):
    return Room.objects.create(code="R1", name="一号")


@pytest.mark.django_db
def test_create_rack(room):
    c = APIClient()
    r = c.post("/api/racks/", {"room": room.id, "name": "A-03",
        "location_code": "A-03-12", "total_u": 42,
        "rated_power_kw": 4.0, "max_weight_kg": 800}, format="json")
    assert r.status_code == 201, r.content
    assert Rack.objects.get(location_code="A-03-12").total_u == 42


@pytest.mark.django_db
def test_total_u_validation(room):
    c = APIClient()
    r = c.post("/api/racks/", {"room": room.id, "name": "A", "location_code": "X",
        "total_u": 0, "rated_power_kw": 4, "max_weight_kg": 800}, format="json")
    assert r.status_code == 400 and "total_u" in r.data["fields"]


@pytest.mark.django_db
def test_rack_in_openapi_schema():
    assert "/api/racks/" in APIClient().get("/api/schema/").data["paths"]


@pytest.mark.django_db
def test_duplicate_location_code_returns_400(room):
    """UniqueValidator must reject a duplicate location_code with 400, not a 500 IntegrityError."""
    c = APIClient()
    payload = {"room": room.id, "name": "A-01", "location_code": "A-01-01",
               "total_u": 42, "rated_power_kw": 4.0, "max_weight_kg": 800}
    r1 = c.post("/api/racks/", payload, format="json")
    assert r1.status_code == 201, r1.content
    r2 = c.post("/api/racks/", payload, format="json")
    assert r2.status_code == 400, r2.content
    assert "location_code" in r2.data["fields"]


@pytest.mark.django_db
def test_update_with_own_location_code_succeeds(room):
    """A rack keeping its own unchanged location_code must still validate (exclude itself)."""
    c = APIClient()
    payload = {"room": room.id, "name": "A-01", "location_code": "A-01-01",
               "total_u": 42, "rated_power_kw": 4.0, "max_weight_kg": 800}
    r1 = c.post("/api/racks/", payload, format="json")
    assert r1.status_code == 201, r1.content
    rack_id = r1.data["id"]
    payload["name"] = "改名"
    r2 = c.put(f"/api/racks/{rack_id}/", payload, format="json")
    assert r2.status_code == 200, r2.content


# ---- update-time capacity validation ----

def _mk_rack_with_placement(room, total_u=42, power=Decimal("4.0"), weight=Decimal("800")):
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
                               total_u=total_u, rated_power_kw=power, max_weight_kg=weight)
    device = Device.objects.create(asset_no="AST-C", name="服务器",
                                   power_w=Decimal("3000"), weight_kg=Decimal("500"), u_size=2)
    Placement.objects.create(device=device, rack=rack, face="A", start_u=1, u_size=2,
                             status="active")
    return rack


@pytest.mark.django_db
def test_rack_put_lowering_total_u_below_used_returns_400(room):
    """total_u 降到已用 U 以下（B 面还有余量但 A 面超）必须 400。"""
    rack = _mk_rack_with_placement(room)
    r = APIClient().put(f"/api/racks/{rack.id}/", {
        "room": room.id, "name": "A", "location_code": "A-01",
        "total_u": 1, "rated_power_kw": "4.0", "max_weight_kg": "800"}, format="json")
    assert r.status_code == 400, r.content
    assert set(r.data.keys()) == {"code", "message", "fields"}


@pytest.mark.django_db
def test_rack_put_lowering_rated_power_below_used_returns_400(room):
    """rated_power_kw 降到已用功率以下必须 400。"""
    rack = _mk_rack_with_placement(room)
    r = APIClient().put(f"/api/racks/{rack.id}/", {
        "room": room.id, "name": "A", "location_code": "A-01",
        "total_u": 42, "rated_power_kw": "2.0", "max_weight_kg": "800"}, format="json")
    assert r.status_code == 400, r.content
    assert set(r.data.keys()) == {"code", "message", "fields"}


@pytest.mark.django_db
def test_rack_put_lowering_max_weight_below_used_returns_400(room):
    """max_weight_kg 降到已用承重以下必须 400。"""
    rack = _mk_rack_with_placement(room)
    r = APIClient().put(f"/api/racks/{rack.id}/", {
        "room": room.id, "name": "A", "location_code": "A-01",
        "total_u": 42, "rated_power_kw": "4.0", "max_weight_kg": "100"}, format="json")
    assert r.status_code == 400, r.content


@pytest.mark.django_db
def test_rack_put_legal_update_still_200(room):
    """不低于当前用量的合法更新必须照常 200（happy path 不变）。"""
    rack = _mk_rack_with_placement(room)
    r = APIClient().put(f"/api/racks/{rack.id}/", {
        "room": room.id, "name": "A-改", "location_code": "A-01",
        "total_u": 42, "rated_power_kw": "5.0", "max_weight_kg": "900"}, format="json")
    assert r.status_code == 200, r.content
    assert r.data["name"] == "A-改"
