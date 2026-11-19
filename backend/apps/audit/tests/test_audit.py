import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.rooms.models import Room
from apps.audit.models import AuditLog

User = get_user_model()


@pytest.mark.django_db
def test_create_writes_audit():
    Room.objects.create(code="R1", name="一号")
    assert AuditLog.objects.filter(target__contains="Room").exists()


@pytest.mark.django_db
def test_update_writes_before_after():
    r = Room.objects.create(code="R1", name="一号")
    r.name = "二号"; r.save()
    log = AuditLog.objects.filter(action="update", target__contains="Room").last()
    assert log.before.get("name") == "一号" and log.after.get("name") == "二号"


@pytest.mark.django_db
def test_audit_in_openapi_schema():
    assert "/api/auditlog/" in APIClient().get("/api/schema/").data["paths"]


# ---- operator capture (AC7 操作人) ----

@pytest.mark.django_db
def test_create_log_has_operator_from_request():
    """Authenticated POST must record the requesting user as AuditLog.operator."""
    u = User.objects.create_user("op", password="x", role="operator")
    c = APIClient(); c.force_authenticate(u)
    assert c.post("/api/rooms/", {"code": "R1", "name": "一号"}, format="json").status_code == 201
    log = AuditLog.objects.filter(action="create", target__contains="Room").last()
    assert log.operator_id == u.id


@pytest.mark.django_db
def test_update_log_has_operator_from_request():
    """Authenticated PUT must record the requesting user as AuditLog.operator."""
    u = User.objects.create_user("op", password="x", role="operator")
    c = APIClient(); c.force_authenticate(u)
    r = Room.objects.create(code="R1", name="一号")
    resp = c.put(f"/api/rooms/{r.id}/", {"code": "R1", "name": "二号"}, format="json")
    assert resp.status_code == 200, resp.content
    log = AuditLog.objects.filter(action="update", target__contains="Room").last()
    assert log.operator_id == u.id


@pytest.mark.django_db
def test_anonymous_log_operator_is_none():
    """Outside a request (or anonymous), operator stays None — no crash."""
    Room.objects.create(code="R1", name="一号")
    log = AuditLog.objects.filter(action="create", target__contains="Room").last()
    assert log.operator is None
