import pytest
from rest_framework.test import APIClient
from apps.rooms.models import Room

@pytest.mark.django_db
def test_create_room():
    c = APIClient()
    r = c.post("/api/rooms/", {"code": "R1", "name": "一号机房", "address": "A栋3层"}, format="json")
    assert r.status_code == 201, r.content
    assert Room.objects.get(code="R1").name == "一号机房"

@pytest.mark.django_db
def test_room_code_unique():
    from django.db import IntegrityError
    Room.objects.create(code="R1", name="一号")
    with pytest.raises(IntegrityError):
        Room.objects.create(code="R1", name="重复")

@pytest.mark.django_db
def test_invalid_code_returns_400():
    c = APIClient()
    r = c.post("/api/rooms/", {"code": "bad code!", "name": "一号"}, format="json")
    assert r.status_code == 400
    assert "code" in r.data["fields"]

@pytest.mark.django_db
def test_duplicate_code_returns_400():
    c = APIClient()
    r1 = c.post("/api/rooms/", {"code": "R1", "name": "一号"}, format="json")
    assert r1.status_code == 201, r1.content
    r2 = c.post("/api/rooms/", {"code": "R1", "name": "重复"}, format="json")
    assert r2.status_code == 400, r2.content
    assert "code" in r2.data["fields"]

@pytest.mark.django_db
def test_update_with_own_code_succeeds():
    c = APIClient()
    r1 = c.post("/api/rooms/", {"code": "R1", "name": "一号"}, format="json")
    assert r1.status_code == 201, r1.content
    room_id = r1.data["id"]
    r2 = c.put(f"/api/rooms/{room_id}/", {"code": "R1", "name": "改名"}, format="json")
    assert r2.status_code == 200, r2.content

@pytest.mark.django_db
def test_room_in_openapi_schema():
    r = APIClient().get("/api/schema/")
    assert "/api/rooms/" in r.data["paths"]
