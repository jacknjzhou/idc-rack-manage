import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_viewer_cannot_write():
    u = User.objects.create_user("viewer", password="x", role="viewer")
    c = APIClient(); c.force_authenticate(u)
    assert c.post("/api/rooms/", {"code": "R1", "name": "一号"}, format="json").status_code == 403


@pytest.mark.django_db
def test_operator_can_write():
    u = User.objects.create_user("op", password="x", role="operator")
    c = APIClient(); c.force_authenticate(u)
    assert c.post("/api/rooms/", {"code": "R1", "name": "一号"}, format="json").status_code == 201
