"""PROTECT 外键删除必须返回统一错误形状的 409，而不是裸 500。"""
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


@pytest.fixture
def rack(room):
    return Rack.objects.create(room=room, name="A", location_code="A-01",
                               total_u=42, rated_power_kw=Decimal("4.0"),
                               max_weight_kg=Decimal("800"))


@pytest.fixture
def device():
    return Device.objects.create(asset_no="AST-1", name="服务器",
                                 power_w=Decimal("300"), weight_kg=Decimal("15"), u_size=2)


def _assert_unified_409(r):
    assert r.status_code == 409, r.content
    assert set(r.data.keys()) == {"code", "message", "fields"}, r.data
    assert r.data["code"] == "protected_error"
    assert r.data["message"]
    assert r.data["fields"] == []


@pytest.mark.django_db
def test_delete_room_with_racks_returns_409(room, rack):
    r = APIClient().delete(f"/api/rooms/{room.id}/")
    _assert_unified_409(r)


@pytest.mark.django_db
def test_delete_rack_with_placements_returns_409(room, rack, device):
    Placement.objects.create(device=device, rack=rack, face="A", start_u=1, u_size=2)
    r = APIClient().delete(f"/api/racks/{rack.id}/")
    _assert_unified_409(r)


@pytest.mark.django_db
def test_delete_device_with_active_placement_returns_409(room, rack, device):
    Placement.objects.create(device=device, rack=rack, face="A", start_u=1, u_size=2)
    r = APIClient().delete(f"/api/devices/{device.id}/")
    _assert_unified_409(r)


@pytest.mark.django_db
def test_delete_unreferenced_still_204():
    """无关联记录的对象删除照常 204。"""
    room = Room.objects.create(code="R2", name="二号")
    device = Device.objects.create(asset_no="AST-FREE", name="空闲设备",
                                   power_w=Decimal("100"), weight_kg=Decimal("5"), u_size=1)
    assert APIClient().delete(f"/api/rooms/{room.id}/").status_code == 204
    assert APIClient().delete(f"/api/devices/{device.id}/").status_code == 204
