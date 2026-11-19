import pytest
from decimal import Decimal
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement
from apps.placements.services import get_rack_usage

@pytest.fixture
def rack():
    room = Room.objects.create(code="R1", name="一号")
    return Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=42, rated_power_kw=Decimal("4.0"), max_weight_kg=Decimal("800"),
        current_load_kw=Decimal("2.0"))

@pytest.mark.django_db
def test_empty_rack_usage(rack):
    u = get_rack_usage(rack)
    assert u["used_u_by_face"] == {"A": 0, "B": 0}
    assert u["remaining_u_by_face"] == {"A": 42, "B": 42}
    assert u["used_power_w"] == 0 and u["remaining_power_w"] == Decimal("4000")
    assert u["remaining_weight_kg"] == Decimal("800")
    assert u["load_ratio"] == Decimal("0.5") and u["load_ratio_is_estimate"] is False

@pytest.mark.django_db
def test_usage_counts_power_only_active(rack):
    d = Device.objects.create(asset_no="D1", name="D1", power_w=Decimal("300"),
                              weight_kg=Decimal("15"), u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=1, u_size=2, status="active")
    r = Device.objects.create(asset_no="D2", name="D2", power_w=Decimal("999"),
                              weight_kg=Decimal("99"), u_size=1)
    Placement.objects.create(device=r, rack=rack, face="B", start_u=1, u_size=1, status="reserved")
    u = get_rack_usage(rack)
    assert u["used_u_by_face"]["A"] == 2 and u["used_u_by_face"]["B"] == 1
    assert u["used_power_w"] == Decimal("300") and u["used_weight_kg"] == Decimal("15")
