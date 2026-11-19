import pytest
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack


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
