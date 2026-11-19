import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement
from apps.placements.validation import validate_placement, get_warnings, LOAD_WARN_RATIO

@pytest.fixture
def rack():
    room = Room.objects.create(code="R1", name="一号")
    return Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"),
        current_load_kw=Decimal("0.9"))

@pytest.mark.django_db
def test_u_conflict_blocked(rack):
    d = Device.objects.create(asset_no="D1", name="D1", power_w=1, weight_kg=1, u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=1, u_size=2)
    with pytest.raises(ValidationError, match="U位冲突"):
        validate_placement(rack, "A", 2, 2, Decimal("1"), Decimal("1"))

@pytest.mark.django_db
def test_over_total_u_blocked(rack):
    with pytest.raises(ValidationError, match="总U数"):
        validate_placement(rack, "A", 9, 2, Decimal("1"), Decimal("1"))

@pytest.mark.django_db
def test_over_power_blocked(rack):
    with pytest.raises(ValidationError, match="功率"):
        validate_placement(rack, "A", 1, 1, Decimal("2000"), Decimal("1"))

@pytest.mark.django_db
def test_over_weight_blocked(rack):
    with pytest.raises(ValidationError, match="承重"):
        validate_placement(rack, "A", 1, 1, Decimal("1"), Decimal("500"))

@pytest.mark.django_db
def test_valid_placement_passes(rack):
    validate_placement(rack, "A", 1, 2, Decimal("100"), Decimal("10"))

@pytest.mark.django_db
def test_load_warning_only(rack):
    assert any("负载率" in x for x in get_warnings(rack))
    assert LOAD_WARN_RATIO == Decimal("0.8")
