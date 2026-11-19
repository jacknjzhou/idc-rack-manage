import pytest
from rest_framework.test import APIClient

from apps.rooms.models import Room
from apps.audit.models import AuditLog


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
