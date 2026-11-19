import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_openapi_schema_served():
    c = APIClient()
    r = c.get("/api/schema/")
    assert r.status_code == 200
    assert "openapi" in r.data and "paths" in r.data

@pytest.mark.django_db
def test_error_response_structure():
    c = APIClient()
    r = c.post("/api/rooms/", {}, format="json")  # 缺必填字段
    assert r.status_code == 400
    assert set(r.data.keys()) == {"code", "message", "fields"}
    assert r.data["code"] == "validation_error"
    assert "code" in r.data["fields"] and "name" in r.data["fields"]
