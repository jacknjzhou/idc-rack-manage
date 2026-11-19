# backend/config/test_schema_coverage.py
import pytest
from rest_framework.test import APIClient

EXPECTED_PATHS = [
    "/api/rooms/", "/api/racks/", "/api/devices/",
    "/api/placements/", "/api/auditlog/",
]

@pytest.mark.django_db
def test_all_endpoints_declared_in_openapi():
    schema = APIClient().get("/api/schema/").data
    paths = schema["paths"]
    for p in EXPECTED_PATHS:
        assert p in paths, f"{p} 未在 OpenAPI schema 中声明"
    # 每个写操作必须声明 requestBody；每个响应必须声明 schema
    for p, methods in paths.items():
        for method, op in methods.items():
            if method in ("post", "put", "patch") and "remove" not in p:
                assert "requestBody" in op, f"{method} {p} 缺少 requestBody schema"
            assert "responses" in op and op["responses"], f"{method} {p} 缺少响应 schema"

@pytest.mark.django_db
def test_validation_error_shape_is_consistent():
    c = APIClient()
    cases = [
        ("post", "/api/rooms/", {"code": "bad code!", "name": "x"}),
        ("post", "/api/racks/", {}),
        ("post", "/api/devices/", {"asset_no": "A", "name": "x", "power_w": -1,
                                   "weight_kg": 1, "u_size": 1}),
        ("post", "/api/placements/", {"face": "C"}),
    ]
    for method, url, payload in cases:
        r = getattr(c, method)(url, payload, format="json")
        assert r.status_code == 400, (url, r.content)
        assert set(r.data.keys()) == {"code", "message", "fields"}, (url, r.data)
        assert r.data["code"] == "validation_error"
        assert len(r.data["fields"]) > 0
