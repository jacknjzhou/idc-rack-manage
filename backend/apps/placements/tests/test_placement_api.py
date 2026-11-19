import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement

@pytest.fixture
def setup():
    room = Room.objects.create(code="R1", name="一号")
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    dev = Device.objects.create(asset_no="D1", name="D1", power_w=100, weight_kg=10, u_size=2)
    return rack, dev

@pytest.mark.django_db
def test_place_device(setup):
    rack, dev = setup
    r = APIClient().post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json")
    assert r.status_code == 201, r.content
    assert Placement.objects.get(id=r.data["id"]).status == "active"

@pytest.mark.django_db
def test_invalid_face_returns_400(setup):
    rack, dev = setup
    r = APIClient().post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "C", "start_u": 1, "u_size": 2}, format="json")
    assert r.status_code == 400 and "face" in r.data["fields"]

@pytest.mark.django_db
def test_place_conflict_returns_400(setup):
    rack, dev = setup
    c = APIClient()
    c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json")
    dev2 = Device.objects.create(asset_no="D2", name="D2", power_w=100, weight_kg=10, u_size=2)
    r = c.post("/api/placements/", {"device": dev2.id, "rack": rack.id,
        "face": "A", "start_u": 2, "u_size": 2}, format="json")
    assert r.status_code == 400 and "U位冲突" in str(r.data)

@pytest.mark.django_db
def test_remove_frees_u(setup):
    rack, dev = setup
    c = APIClient()
    p = c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    assert c.post(f"/api/placements/{p['id']}/remove/", {}, format="json").status_code == 200
    assert Placement.objects.get(id=p["id"]).status == "removed"

@pytest.mark.django_db
def test_move_to_other_rack(setup):
    rack, dev = setup
    rack2 = Rack.objects.create(room=rack.room, name="B", location_code="B-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    c = APIClient()
    p = c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    r = c.post(f"/api/placements/{p['id']}/move/", {"rack": rack2.id,
        "face": "A", "start_u": 3}, format="json")
    assert r.status_code == 200, r.content
    obj = Placement.objects.get(id=p["id"])
    assert obj.rack_id == rack2.id and obj.start_u == 3
