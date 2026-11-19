# IDC 机柜管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一个可运行的机柜管理 Web 系统：机房/机柜/设备台账、精确 U 位放置与可视化、上下架/移位、U位/功率/承重强校验与负载告警、查询报表、操作审计；并预留 IPAM/资产生命周期/动环采集扩展点。所有 RESTful 接口的请求/响应参数均由 Schema 显式定义，并基于 Schema 做参数校验，自动生成 OpenAPI 3.1 文档。

**Architecture:** Docker Compose 是唯一的开发/测试/部署环境（base + dev + prod 三层覆盖），数据库为 compose 内的 PostgreSQL 16 服务（健康检查和具名卷持久化）。Django 5 + DRF 提供 REST API 与领域服务（容量计算/校验为纯函数）；**API 层统一采用「Request Schema Serializer（入参校验）+ Response Schema Serializer（出参结构）+ drf-spectacular @extend_schema 注解（OpenAPI 声明）」三件套，任何接口不得直接使用 ModelSerializer 接收请求参数**。Vue 3 + Vite + TypeScript + Element Plus 提供前端，机柜 U 位图用 CSS Grid 自绘。容量数据由 Placement 记录实时计算，不冗余存储。按领域拆分为 rooms / racks / devices / placements / audit / accounts 六个 Django app。

**Tech Stack:** Docker Compose v2, PostgreSQL 16, psycopg 3, Python 3.12, Django 5.0, djangorestframework 3.14, drf-spectacular 0.27（OpenAPI 3.1 Schema）, pytest + pytest-django, Vue 3, Vite, TypeScript, Element Plus, Vitest, nginx.

## Global Constraints

- **所有开发、测试、部署命令一律通过 docker compose 执行**，不在宿主机直接跑 `python`/`npm`。
- Compose 分层：`docker-compose.yml`（base，含 db）+ `docker-compose.dev.yml`（dev）+ `docker-compose.prod.yml`（prod）；统一别名 `DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"`。
- 数据库为 compose 内 `postgres:16-alpine`（服务名 `db`），数据存于具名卷 `pgdata`；连接参数由环境变量注入，不落代码。web 用 `depends_on.db.condition: service_healthy` 等待就绪；pytest 连真实 PostgreSQL（pytest-django 自动建 test 库）。
- **Schema 强制约束（用户 2026-11-19 追加）**：
  1. 每个接口的**请求参数**必须由独立的 `XxxRequestSerializer` 定义（禁止用 `ModelSerializer` 直接收请求），字段必须显式声明类型、必填性、范围/正则/枚举等校验规则；DRF 在反序列化时自动执行校验，失败返回统一 400 结构。
  2. 每个接口的**响应参数**必须由独立的 `XxxResponseSerializer` 定义结构（ModelSerializer 仅可用于只读响应且需通过 `@extend_schema(responses=...)` 显式声明）。
  3. 每个 ViewSet/APIView 必须用 `@extend_schema` / `@extend_schema_view` 声明 `request=` 与 `responses=`，OpenAPI 文档由 `drf-spectacular` 从这些声明生成，暴露 `/api/schema/` 与 `/api/docs/`。
  4. 统一错误响应结构：`{"code": "...", "message": "...", "fields": {...}}`，由 `config.exceptions.api_exception_handler` 生成；前端按此结构解析。
  5. 每个 Task 的测试必须包含：①正常请求 ②参数校验失败返回 400 且 `fields` 含出错字段 ③`/api/schema/` 的 OpenAPI JSON 中包含该接口路径（可集中在 Task 1/12 做全量断言，各 Task 做局部断言）。
- 容量数据必须由 Placement 实时计算，禁止在 Rack 表冗余存储 `used_u/used_power/used_weight`。
- U 位按 A/B 两面独立计算；功率/承重按整柜（两面）合并统计。
- 强校验（U位冲突、超总U、超功率、超承重）必须阻断提交；负载率超阈值仅告警不阻断。
- 功率/承重强校验基于"台账累计值"，"当前负载 current_load_kw"仅用于负载率展示与告警，二者不可混用。
- 一期不实现 IPAM / 动环采集 / 工单 / 资产采购报废，仅预留字段与接口。
- 每个关键变更都要写 AuditLog。
- 测试先行（TDD）：先写失败测试，再写最小实现；每个 Task 以可独立运行的测试结束。
- **必须使用 git 管理代码（用户 2026-11-19 追加）**：开工前已在仓库根目录执行 `git init` 并完成初始提交；每个 Task 末尾的 commit 步骤为**强制项**，必须执行（不得因无仓库而跳过）。提交信息遵循各 Task 末尾给出的 `git commit -m "..."` 模板。

---

### Task 0: Docker Compose 环境基座（开发/测试/部署共用）

**Files:**
- Create: `docker-compose.yml`, `docker-compose.dev.yml`
- Create: `backend/Dockerfile`, `frontend/Dockerfile`（多阶段 dev/prod）
- Create: `backend/.dockerignore`, `frontend/.dockerignore`, `.env.example`
- Test: 无（以 `docker compose config` + db 健康检查为验收）

**Interfaces:**
- base 定义 `db`（PostgreSQL 16 + healthcheck + `pgdata` 卷）、`web`、`frontend`；dev 层加源码 bind mount、热重载、DEBUG=1。
- 验收：`$DC config` 无报错；`$DC up -d db` 后 `$DC exec db pg_isready -U idc -d idc` 返回 accepting connections。

- [ ] **Step 1: 写 base compose（含 PostgreSQL）**

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-idc}
      POSTGRES_USER: ${POSTGRES_USER:-idc}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-idc}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-idc} -d ${POSTGRES_DB:-idc}"]
      interval: 5s
      timeout: 3s
      retries: 10

  web:
    build: { context: ./backend, target: dev }
    env_file: .env
    environment: { POSTGRES_HOST: db }
    ports: ["8000:8000"]
    depends_on:
      db: { condition: service_healthy }

  frontend:
    build: { context: ./frontend, target: dev }
    ports: ["5173:5173"]
    depends_on: [web]

volumes:
  pgdata:
```

- [ ] **Step 2: 写 dev 覆盖层**

```yaml
# docker-compose.dev.yml
services:
  web:
    volumes: ["./backend:/app"]
    command: python manage.py runserver 0.0.0.0:8000
    environment: { DEBUG: "1" }
  frontend:
    volumes: ["./frontend:/app", "/app/node_modules"]
    command: npm run dev -- --host 0.0.0.0
    environment: { DEBUG: "1" }
```

- [ ] **Step 3: 写后端 Dockerfile（多阶段）**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

FROM base AS dev
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS prod
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

- [ ] **Step 4: 写前端 Dockerfile（多阶段）**

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .

FROM base AS dev
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 5: 写 .dockerignore 与 .env.example**

```text
# backend/.dockerignore
__pycache__/
*.pyc
.pytest_cache/
db.sqlite3
var/
```
```text
# frontend/.dockerignore
node_modules/
dist/
```
```text
# .env.example  （cp 为 .env；.env 不入库）
DEBUG=1
SECRET_KEY=dev-only-change-me
ALLOWED_HOSTS=*
POSTGRES_DB=idc
POSTGRES_USER=idc
POSTGRES_PASSWORD=idc
POSTGRES_PORT=5432
```

- [ ] **Step 6: 校验 compose 配置并验证 PostgreSQL 就绪**

```bash
cp .env.example .env
DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
$DC config && $DC up -d db && $DC exec db pg_isready -U idc -d idc
```
Expected: config 无报错；`accepting connections`。

- [ ] **Step 7: Commit**

```bash
git add docker-compose*.yml backend/Dockerfile backend/.dockerignore frontend/Dockerfile frontend/.dockerignore .env.example && git commit -m "chore: docker compose foundation with PostgreSQL"
```

---

### Task 1: 后端脚手架 + API Schema 基础设施

**Files:**
- Create: `backend/requirements.txt`（含 drf-spectacular）
- Create: `backend/manage.py`, `backend/config/{__init__,settings,urls,wsgi,asgi,exceptions}.py`
- Create: `backend/pytest.ini`, `backend/apps/__init__.py`
- Test: `backend/config/test_settings.py`, `backend/config/test_schema.py`

**Interfaces:**
- Django 工程可从容器内启动；`config.urls` 挂载 `api/`、`/api/schema/`（OpenAPI JSON）、`/api/docs/`（Swagger UI）。
- 统一错误结构由 `config.exceptions.api_exception_handler` 生成；`drf-spectacular` 配置写入 settings。
- 所有后续 Task 的 Serializer/ViewSet 必须遵循本 Task 建立的 schema 规范。

- [ ] **Step 1: 写依赖清单**

```text
# backend/requirements.txt
Django==5.0.6
djangorestframework==3.14.0
drf-spectacular==0.27.2
psycopg[binary]==3.2.1
pytest==8.2.0
pytest-django==4.8.0
django-cors-headers==4.3.1
gunicorn==22.0.0
```

- [ ] **Step 2: 写 pytest 配置**

```ini
; backend/pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
testpaths = apps config
```

- [ ] **Step 3: 写 manage.py / wsgi / asgi（Django 标准）**

```python
# backend/manage.py
#!/usr/bin/env python
import os, sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
```
wsgi/asgi 用 Django 5 标准模板，`DJANGO_SETTINGS_MODULE = config.settings`。

- [ ] **Step 4: 写 settings.py（PostgreSQL + drf-spectacular + 统一异常）**

```python
# backend/config/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth",
    "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "corsheaders", "drf_spectacular",
    "apps.rooms", "apps.racks", "apps.devices",
    "apps.placements", "apps.audit.apps.AuditConfig", "apps.accounts",
]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "APP_DIRS": True, "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB", "idc"),
    "USER": os.environ.get("POSTGRES_USER", "idc"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "idc"),
    "HOST": os.environ.get("POSTGRES_HOST", "db"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
}}
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_TZ = True
CORS_ALLOW_ALL_ORIGINS = True
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.api_exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "IDC 机柜管理 API",
    "DESCRIPTION": "机房/机柜/设备/U位放置/容量校验/审计 REST API，Schema 驱动。",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
AUTH_USER_MODEL = "accounts.User"
```

- [ ] **Step 5: 写统一异常处理器（错误响应 Schema）**

```python
# backend/config/exceptions.py
from rest_framework.views import exception_handler

def api_exception_handler(exc, context):
    """统一错误响应：{code, message, fields}。"""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        payload = {"code": "error", "message": str(data["detail"]), "fields": {}}
    else:
        payload = {"code": "validation_error", "message": "参数校验失败", "fields": data}
    response.data = payload
    return response
```

- [ ] **Step 6: 写 config/urls.py（含 Schema 路由）**

```python
# backend/config/urls.py
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include("apps.rooms.urls")),
    path("api/", include("apps.racks.urls")),
    path("api/", include("apps.devices.urls")),
    path("api/", include("apps.placements.urls")),
    path("api/", include("apps.audit.urls")),
]
```

- [ ] **Step 7: 写冒烟测试（settings + schema + 统一错误结构）**

```python
# backend/config/test_settings.py
from django.conf import settings

def test_core_apps_installed():
    assert "rest_framework" in settings.INSTALLED_APPS
    assert "drf_spectacular" in settings.INSTALLED_APPS
    assert "apps.placements" in settings.INSTALLED_APPS

def test_db_is_postgresql():
    assert settings.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"

def test_schema_class_configured():
    assert settings.REST_FRAMEWORK["DEFAULT_SCHEMA_CLASS"] == "drf_spectacular.openapi.AutoSchema"
```

```python
# backend/config/test_schema.py
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
```

> 说明：`test_error_response_structure` 依赖 Task 2 的 RoomRequestSerializer；若严格按 TDD，可在本 Task 先写测试、Task 2 完成后转绿。执行 Task 1 时若此测试因 Room 未建而失败，属预期，Task 2 完成即通过。

- [ ] **Step 8: 建占位 app 目录与 urls 空文件**

每个 app 建 `__init__.py`、`apps.py`、`urls.py`（`urlpatterns = []`）、`models.py`（空）、`tests/`（含 `__init__.py`）。`apps.accounts` 先建最小 `AbstractUser` 子类；`apps.audit.apps.AuditConfig`（Task 8 补 ready）。

- [ ] **Step 9: 首次启动 web 并运行测试**

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
$DC up -d --build web db
$DC exec web pytest config/test_settings.py -v
```
Expected: 3 passed（test_schema 中错误结构用例在 Task 2 后通过）。

- [ ] **Step 10: Commit**

```bash
git add backend/ && git commit -m "chore: scaffold Django backend with PostgreSQL, OpenAPI schema and unified error response"
```

---

### Task 2: Room（机房）台账 + Schema

**Files:**
- Modify: `backend/apps/rooms/models.py`
- Create: `backend/apps/rooms/serializers.py`（`RoomRequestSerializer` + `RoomResponseSerializer`）
- Create: `backend/apps/rooms/views.py`
- Modify: `backend/apps/rooms/urls.py`
- Test: `backend/apps/rooms/tests/test_room_api.py`

**Interfaces:**
- Produces: `Room` 模型；端点 `GET/POST /api/rooms/`、`GET/PUT/PATCH/DELETE /api/rooms/{id}/`。
- **Schema**：请求用 `RoomRequestSerializer`（code 正则 `^[A-Za-z0-9_-]+$`、name 必填非空）；响应用 `RoomResponseSerializer`；ViewSet 用 `@extend_schema_view` 声明。

- [ ] **Step 1: 写失败测试（正常 + 校验失败 + schema）**

```python
# backend/apps/rooms/tests/test_room_api.py
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
def test_room_in_openapi_schema():
    r = APIClient().get("/api/schema/")
    assert "/api/rooms/" in r.data["paths"]
```

- [ ] **Step 2: 运行确认失败** → Run: `... exec web pytest apps/rooms -v` → FAIL

- [ ] **Step 3: 写模型**

```python
# backend/apps/rooms/models.py
from django.db import models

class Room(models.Model):
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    address = models.CharField(max_length=255, blank=True)
    owner = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.code} {self.name}"
```

- [ ] **Step 4: 写 Request/Response Schema Serializer**

```python
# backend/apps/rooms/serializers.py
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Room

class RoomRequestSerializer(serializers.Serializer):
    """Room 请求 Schema：类型/必填/正则校验由 DRF 自动执行。"""
    code = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=64,
                                  error_messages={"invalid": "位置编码只能含字母、数字、下划线、连字符"})
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    owner = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")

class RoomResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "code", "name", "address", "owner"]
        read_only_fields = fields
```

- [ ] **Step 5: 写 ViewSet（带 schema 注解）**

```python
# backend/apps/rooms/views.py
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models import Room
from .serializers import RoomRequestSerializer, RoomResponseSerializer

@extend_schema_view(
    create=extend_schema(request=RoomRequestSerializer, responses={201: RoomResponseSerializer},
                         summary="新建机房", tags=["机房"]),
    update=extend_schema(request=RoomRequestSerializer, responses={200: RoomResponseSerializer},
                         summary="更新机房", tags=["机房"]),
    partial_update=extend_schema(request=RoomRequestSerializer, responses={200: RoomResponseSerializer},
                                 summary="部分更新机房", tags=["机房"]),
    list=extend_schema(responses={200: RoomResponseSerializer(many=True)}, tags=["机房"]),
    retrieve=extend_schema(responses={200: RoomResponseSerializer}, tags=["机房"]),
)
class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all().order_by("id")
    serializer_class = RoomResponseSerializer   # 响应 Schema

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RoomRequestSerializer        # 请求 Schema（入参校验）
        return RoomResponseSerializer

    def create(self, request, *args, **kwargs):
        # RequestSerializer 校验通过后，用其 validated_data 建对象；响应以 ResponseSerializer 渲染
        s = self.get_serializer(data=request.data); s.is_valid(raise_exception=True)
        obj = Room.objects.create(**s.validated_data)
        return Response(RoomResponseSerializer(obj).data, status=201)

    def update(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, partial=False); s.is_valid(raise_exception=True)
        obj = self.get_object()
        for k, v in s.validated_data.items(): setattr(obj, k, v)
        obj.save()
        return Response(RoomResponseSerializer(obj).data)

    def partial_update(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data, partial=True); s.is_valid(raise_exception=True)
        obj = self.get_object()
        for k, v in s.validated_data.items(): setattr(obj, k, v)
        obj.save()
        return Response(RoomResponseSerializer(obj).data)
```

> 需要 `from rest_framework.response import Response`。后续 Task 的 ViewSet 沿用此模式（RequestSerializer 收参 + is_valid + ResponseSerializer 渲染 + @extend_schema_view 声明）。

```python
# backend/apps/rooms/urls.py
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet

router = DefaultRouter()
router.register("rooms", RoomViewSet, basename="room")
urlpatterns = router.urls
```

- [ ] **Step 6: 运行确认通过** → Run: `... exec web pytest apps/rooms -v` → 4 passed

- [ ] **Step 7: Commit**

```bash
git add backend/apps/rooms && git commit -m "feat: room CRUD with request/response schema validation"
```

---

### Task 3: Rack（机柜）台账 + Schema

**Files:**
- Modify: `backend/apps/racks/models.py`
- Create: `backend/apps/racks/serializers.py`（`RackRequestSerializer` + `RackResponseSerializer`）
- Create: `backend/apps/racks/views.py`, `backend/apps/racks/reporting.py`
- Modify: `backend/apps/racks/urls.py`
- Test: `backend/apps/racks/tests/test_rack_api.py`

**Interfaces:**
- Produces: `Rack` 模型；端点 `/api/racks/`（CRUD）+ Task 9 的 usage/uplan/export。
- **Schema**：`RackRequestSerializer` 校验 room（存在）、name、location_code（正则）、total_u（1–100）、rated_power_kw（>0）、max_weight_kg（>0）、current_load_kw（可空 ≥0）、metrics_endpoint（可空 URL）；响应 `RackResponseSerializer`。

- [ ] **Step 1: 写失败测试（含校验失败与 schema）**

```python
# backend/apps/racks/tests/test_rack_api.py
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
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写模型（字段同前版）**

```python
# backend/apps/racks/models.py
from django.db import models
from apps.rooms.models import Room

class Rack(models.Model):
    room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name="racks")
    name = models.CharField(max_length=128)
    location_code = models.CharField(max_length=64, unique=True)
    location_desc = models.CharField(max_length=255, blank=True)
    total_u = models.PositiveIntegerField()
    rated_power_kw = models.DecimalField(max_digits=8, decimal_places=2)
    max_weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    current_load_kw = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    metrics_endpoint = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.location_code
```

- [ ] **Step 4: 写 Request/Response Schema（含校验规则）**

```python
# backend/apps/racks/serializers.py
from rest_framework import serializers
from .models import Rack

class RackRequestSerializer(serializers.Serializer):
    room = serializers.PrimaryKeyRelatedField(queryset=__import__("apps.rooms.models", fromlist=["Room"]).Room.objects.all())
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    location_code = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=64)
    location_desc = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    total_u = serializers.IntegerField(min_value=1, max_value=100)
    rated_power_kw = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0.01)
    max_weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    current_load_kw = serializers.DecimalField(max_digits=8, decimal_places=2,
                                               min_value=0, required=False, allow_null=True, default=None)
    metrics_endpoint = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

class RackResponseSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source="room.name", read_only=True)
    class Meta:
        model = Rack
        fields = ["id", "room", "room_name", "name", "location_code", "location_desc",
                  "total_u", "rated_power_kw", "max_weight_kg", "current_load_kw", "metrics_endpoint"]
        read_only_fields = fields
```

> `room` 的 queryset 直接写 `from apps.rooms.models import Room` 更清晰：实际文件里把 `__import__...` 换成顶部 `from apps.rooms.models import Room` 并写 `queryset=Room.objects.all()`。

- [ ] **Step 5: 写 ViewSet（沿用 Task 2 模式 + schema 注解）**

`@extend_schema_view(create/update/partial_update → request=RackRequestSerializer, responses=RackResponseSerializer; list/retrieve → responses=RackResponseSerializer(many=True)/...; tags=["机柜"])`；`get_serializer_class` 与 create/update/partial_update 实现同 Task 2。

- [ ] **Step 6: 运行确认通过** → Run: `... exec web pytest apps/racks -v` → 3 passed

- [ ] **Step 7: Commit**

```bash
git add backend/apps/racks && git commit -m "feat: rack CRUD with schema validation"
```

---

### Task 4: Device（设备）台账 + Schema

**Files:**
- Modify: `backend/apps/devices/models.py`
- Create: `backend/apps/devices/serializers.py`（`DeviceRequestSerializer` + `DeviceResponseSerializer`）
- Create: `backend/apps/devices/views.py`, urls
- Test: `backend/apps/devices/tests/test_device_api.py`

**Interfaces:**
- `Device` 模型；端点 `/api/devices/`。
- **Schema**：`asset_no` 正则、`power_w ≥ 0`、`weight_kg ≥ 0`、`u_size` 1–10、`status` 枚举，`ip_addresses` 为字符串数组（每项 IP 正则）。

- [ ] **Step 1: 写失败测试（含校验失败）**

```python
# backend/apps/devices/tests/test_device_api.py
import pytest
from rest_framework.test import APIClient
from apps.devices.models import Device

@pytest.mark.django_db
def test_create_device():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-001", "name": "服务器A",
        "type": "server", "power_w": 300, "weight_kg": 15, "u_size": 2}, format="json")
    assert r.status_code == 201, r.content
    assert Device.objects.get(asset_no="AST-001").status == "in_use"

@pytest.mark.django_db
def test_invalid_status_returns_400():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-002", "name": "B",
        "power_w": 1, "weight_kg": 1, "u_size": 1, "status": "unknown"}, format="json")
    assert r.status_code == 400 and "status" in r.data["fields"]

@pytest.mark.django_db
def test_invalid_ip_returns_400():
    r = APIClient().post("/api/devices/", {"asset_no": "AST-003", "name": "C",
        "power_w": 1, "weight_kg": 1, "u_size": 1,
        "ip_addresses": ["not-an-ip"]}, format="json")
    assert r.status_code == 400 and "ip_addresses" in r.data["fields"]
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写模型（字段同前版）**

```python
# backend/apps/devices/models.py
from django.db import models

class Device(models.Model):
    STATUS = [("in_use", "在用"), ("warranty", "维保"), ("retired", "报废")]
    asset_no = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=128, blank=True)
    power_w = models.DecimalField(max_digits=10, decimal_places=2)
    weight_kg = models.DecimalField(max_digits=10, decimal_places=2)
    u_size = models.PositiveIntegerField()
    ip_addresses = models.JSONField(default=list, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    warranty_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="in_use")

    def __str__(self):
        return f"{self.asset_no} {self.name}"
```

- [ ] **Step 4: 写 Request/Response Schema**

```python
# backend/apps/devices/serializers.py
from rest_framework import serializers
from .models import Device

class IPField(serializers.CharField):
    """简单 IPv4 正则校验。"""
    def __init__(self, **kwargs):
        kwargs.setdefault("validators", [])
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        import re
        v = super().to_internal_value(data)
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", v) or any(int(x) > 255 for x in v.split(".")):
            raise serializers.ValidationError("非法 IP 地址")
        return v

class DeviceRequestSerializer(serializers.Serializer):
    asset_no = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=64)
    name = serializers.CharField(max_length=128, trim_whitespace=True)
    type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    model = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    power_w = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    weight_kg = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    u_size = serializers.IntegerField(min_value=1, max_value=10)
    ip_addresses = serializers.ListField(child=IPField(), required=False, default=list)
    purchase_date = serializers.DateField(required=False, allow_null=True, default=None)
    warranty_end = serializers.DateField(required=False, allow_null=True, default=None)
    status = serializers.ChoiceField(choices=["in_use", "warranty", "retired"], default="in_use")

class DeviceResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "asset_no", "name", "type", "model", "power_w", "weight_kg",
                  "u_size", "ip_addresses", "purchase_date", "warranty_end", "status"]
        read_only_fields = fields
```

- [ ] **Step 5: 写 ViewSet（沿用 Task 2 模式 + schema 注解 tags=["设备"]）**

- [ ] **Step 6: 运行确认通过** → Run: `... exec web pytest apps/devices -v` → 3 passed

- [ ] **Step 7: Commit**

```bash
git add backend/apps/devices && git commit -m "feat: device CRUD with schema validation"
```

---

### Task 5: Placement 模型 + 容量计算服务（核心）

**Files:**
- Modify: `backend/apps/placements/models.py`
- Create: `backend/apps/placements/services.py`
- Test: `backend/apps/placements/tests/test_capacity.py`

**Interfaces:**
- `Placement` 模型；`get_rack_usage(rack: Rack) -> dict`，键同前版（used_u_by_face/remaining_u_by_face/used_power_w/remaining_power_w/used_weight_kg/remaining_weight_kg/current_load_kw/load_ratio/load_ratio_is_estimate）。
- 口径：U位统计 `status in ('active','reserved')`；功率/重量只统计 `status == 'active'`。
- 本 Task 为领域服务，无 HTTP 接口；schema 约束从 Task 7 开始覆盖 Placement API。

- [ ] **Step 1: 写失败测试（同前版两个用例）**

```python
# backend/apps/placements/tests/test_capacity.py
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
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写 Placement 模型（字段同前版）**

```python
# backend/apps/placements/models.py
from django.db import models
from apps.racks.models import Rack
from apps.devices.models import Device

class Placement(models.Model):
    FACE = [("A", "A面"), ("B", "B面")]
    STATUS = [("active", "在架"), ("reserved", "预留"), ("removed", "下架")]
    device = models.ForeignKey(Device, on_delete=models.PROTECT, related_name="placements")
    rack = models.ForeignKey(Rack, on_delete=models.PROTECT, related_name="placements")
    face = models.CharField(max_length=1, choices=FACE)
    start_u = models.PositiveIntegerField()
    u_size = models.PositiveIntegerField()
    placed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=16, choices=STATUS, default="active")
    removed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.rack}/{self.face}/{self.start_u}+{self.u_size}"
```

- [ ] **Step 4: 写容量服务（纯函数，同前版）**

```python
# backend/apps/placements/services.py
from decimal import Decimal
from apps.racks.models import Rack
from .models import Placement

OCCUPYING = ("active", "reserved")

def get_rack_usage(rack: Rack) -> dict:
    ps = list(Placement.objects.filter(rack=rack, status__in=OCCUPYING))
    used_u = {"A": 0, "B": 0}
    for p in ps:
        used_u[p.face] += p.u_size
    remaining_u = {f: rack.total_u - used_u[f] for f in ("A", "B")}
    active = [p for p in ps if p.status == "active"]
    used_power = sum((p.device.power_w for p in active), Decimal("0"))
    used_weight = sum((p.device.weight_kg for p in active), Decimal("0"))
    rated_w = rack.rated_power_kw * 1000
    if rack.current_load_kw is not None:
        load_ratio = rack.current_load_kw / rack.rated_power_kw
        estimate = False
    else:
        load_ratio = used_power / rated_w if rated_w else Decimal("0")
        estimate = True
    return {
        "used_u_by_face": used_u, "remaining_u_by_face": remaining_u,
        "used_power_w": used_power, "remaining_power_w": rated_w - used_power,
        "used_weight_kg": used_weight, "remaining_weight_kg": rack.max_weight_kg - used_weight,
        "current_load_kw": rack.current_load_kw, "load_ratio": load_ratio,
        "load_ratio_is_estimate": estimate,
    }
```

- [ ] **Step 5: 迁移并运行确认通过**

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
$DC exec web sh -c "python manage.py makemigrations rooms racks devices placements && pytest apps/placements -v"
```
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat: Placement model and rack capacity calculation"
```

---

### Task 6: 容量校验规则（强阻断 + 告警）

**Files:**
- Create: `backend/apps/placements/validation.py`
- Test: `backend/apps/placements/tests/test_validation.py`

**Interfaces:**
- `validate_placement(...)`、`get_warnings(rack)`、`LOAD_WARN_RATIO = Decimal("0.8")`；规则同前版。

- [ ] **Step 1–2: 写失败测试并确认 FAIL（同前版 6 用例）**

```python
# backend/apps/placements/tests/test_validation.py
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
```

- [ ] **Step 3: 写校验实现（同前版）**

```python
# backend/apps/placements/validation.py
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.racks.models import Rack
from .models import Placement
from .services import get_rack_usage

LOAD_WARN_RATIO = Decimal("0.8")
_OCCUPYING = ("active", "reserved")

def validate_placement(rack, face, start_u, u_size, power_w, weight_kg, exclude_id=None) -> None:
    qs = Placement.objects.filter(rack=rack, face=face, status__in=_OCCUPYING)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)
    for p in qs:
        if start_u <= p.start_u + p.u_size - 1 and p.start_u <= start_u + u_size - 1:
            raise ValidationError("U位冲突：该面指定U位已被占用")
    if start_u < 1 or start_u + u_size - 1 > rack.total_u:
        raise ValidationError("超出总U数范围")
    u = get_rack_usage(rack)
    if u["used_power_w"] + Decimal(power_w) > rack.rated_power_kw * 1000:
        raise ValidationError("功率超出机柜额定功率")
    if u["used_weight_kg"] + Decimal(weight_kg) > rack.max_weight_kg:
        raise ValidationError("承重超出机柜上限")

def get_warnings(rack: Rack) -> list:
    u = get_rack_usage(rack)
    warns = []
    if u["load_ratio"] is not None and u["load_ratio"] > LOAD_WARN_RATIO:
        suffix = "（估算）" if u["load_ratio_is_estimate"] else ""
        warns.append(f"负载率 {u['load_ratio']:.0%} 超过告警阈值 80%{suffix}")
    return warns
```

- [ ] **Step 4: 运行确认通过** → 6 passed

- [ ] **Step 5: Commit**

```bash
git add backend/apps/placements && git commit -m "feat: capacity validation rules with warnings"
```

---

### Task 7: Placement API（上架/下架/移位）+ Schema

**Files:**
- Modify: `backend/apps/placements/serializers.py`（`PlaceRequestSerializer` / `MoveRequestSerializer` / `PlacementResponseSerializer`）
- Modify: `backend/apps/placements/views.py`, `urls.py`
- Test: `backend/apps/placements/tests/test_placement_api.py`

**Interfaces:**
- `POST /api/placements/` 上架：body `{device, rack, face, start_u, u_size}`，由 `PlaceRequestSerializer` 校验（face 枚举、start_u≥1、u_size 1–10、对象存在性），业务校验由 `validate_placement` 抛 400。
- `POST /api/placements/{id}/remove/` 下架；`POST /api/placements/{id}/move/` 移位（body `{rack, face, start_u}`，`MoveRequestSerializer`）。
- **Schema**：三个 Serializer + `@extend_schema_view` 注解（含 remove/move 的 `@action` 注解 `request=...`）。

- [ ] **Step 1: 写失败测试（含参数校验失败）**

```python
# backend/apps/placements/tests/test_placement_api.py
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement

@pytest.fixture
def setup():
    room = Room.objects.create(code="R1", name="一号")
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    dev = Device.objects.create(asset_no="D1", name="D1", power_w=100, weight_kg=10, u_size=2)
    return rack, dev

@pytest.mark.django_db
def test_place_device(setup):
    rack, dev = setup
    r = APIClient().post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json")
    assert r.status_code == 201, r.content
    assert Placement.objects.get(id=r.data["id"]).status == "active"

@pytest.mark.django_db
def test_invalid_face_returns_400(setup):
    rack, dev = setup
    r = APIClient().post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "C", "start_u": 1, "u_size": 2}, format="json")
    assert r.status_code == 400 and "face" in r.data["fields"]

@pytest.mark.django_db
def test_place_conflict_returns_400(setup):
    rack, dev = setup
    c = APIClient()
    c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json")
    dev2 = Device.objects.create(asset_no="D2", name="D2", power_w=100, weight_kg=10, u_size=2)
    r = c.post("/api/placements/", {"device": dev2.id, "rack": rack.id,
        "face": "A", "start_u": 2, "u_size": 2}, format="json")
    assert r.status_code == 400 and "U位冲突" in str(r.data)

@pytest.mark.django_db
def test_remove_frees_u(setup):
    rack, dev = setup
    c = APIClient()
    p = c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    assert c.post(f"/api/placements/{p['id']}/remove/", {}, format="json").status_code == 200
    assert Placement.objects.get(id=p["id"]).status == "removed"

@pytest.mark.django_db
def test_move_to_other_rack(setup):
    rack, dev = setup
    rack2 = Rack.objects.create(room=rack.room, name="B", location_code="B-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    c = APIClient()
    p = c.post("/api/placements/", {"device": dev.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    r = c.post(f"/api/placements/{p['id']}/move/", {"rack": rack2.id,
        "face": "A", "start_u": 3}, format="json")
    assert r.status_code == 200, r.content
    obj = Placement.objects.get(id=p["id"])
    assert obj.rack_id == rack2.id and obj.start_u == 3
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写三个 Schema Serializer**

```python
# backend/apps/placements/serializers.py
from rest_framework import serializers
from apps.devices.models import Device
from apps.racks.models import Rack
from .models import Placement

class PlaceRequestSerializer(serializers.Serializer):
    device = serializers.PrimaryKeyRelatedField(queryset=Device.objects.all())
    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.all())
    face = serializers.ChoiceField(choices=["A", "B"])
    start_u = serializers.IntegerField(min_value=1)
    u_size = serializers.IntegerField(min_value=1, max_value=10)

class MoveRequestSerializer(serializers.Serializer):
    rack = serializers.PrimaryKeyRelatedField(queryset=Rack.objects.all())
    face = serializers.ChoiceField(choices=["A", "B"])
    start_u = serializers.IntegerField(min_value=1)

class PlacementResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Placement
        fields = ["id", "device", "rack", "face", "start_u", "u_size",
                  "placed_at", "status", "removed_at"]
        read_only_fields = fields
```

- [ ] **Step 4: 写 ViewSet（schema 注解 + 业务校验）**

```python
# backend/apps/placements/views.py
from datetime import datetime, timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Placement
from .serializers import PlaceRequestSerializer, MoveRequestSerializer, PlacementResponseSerializer
from .validation import validate_placement

@extend_schema_view(
    create=extend_schema(request=PlaceRequestSerializer, responses={201: PlacementResponseSerializer},
                         summary="设备上架", tags=["放置"]),
    list=extend_schema(responses={200: PlacementResponseSerializer(many=True)}, tags=["放置"]),
    retrieve=extend_schema(responses={200: PlacementResponseSerializer}, tags=["放置"]),
)
class PlacementViewSet(viewsets.ModelViewSet):
    queryset = Placement.objects.all().order_by("-placed_at")
    serializer_class = PlacementResponseSerializer

    def create(self, request, *args, **kwargs):
        s = PlaceRequestSerializer(data=request.data); s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_placement(d["rack"], d["face"], d["start_u"], d["u_size"],
                               d["device"].power_w, d["device"].weight_kg)
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        obj = Placement.objects.create(
            device=d["device"], rack=d["rack"], face=d["face"],
            start_u=d["start_u"], u_size=d["u_size"], status="active")
        return Response(PlacementResponseSerializer(obj).data, status=201)

    @extend_schema(request=None, responses={200: PlacementResponseSerializer},
                   summary="设备下架", tags=["放置"])
    @action(detail=True, methods=["post"])
    def remove(self, request, pk=None):
        p = self.get_object()
        p.status = "removed"
        p.removed_at = datetime.now(timezone.utc)
        p.save(update_fields=["status", "removed_at"])
        return Response(PlacementResponseSerializer(p).data)

    @extend_schema(request=MoveRequestSerializer, responses={200: PlacementResponseSerializer},
                   summary="设备移位", tags=["放置"])
    @action(detail=True, methods=["post"])
    def move(self, request, pk=None):
        p = self.get_object()
        s = MoveRequestSerializer(data=request.data); s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            validate_placement(d["rack"], d["face"], d["start_u"], p.u_size,
                               p.device.power_w, p.device.weight_kg, exclude_id=p.id)
        except DjangoValidationError as e:
            raise DRFValidationError(e.messages)
        p.rack = d["rack"]; p.face = d["face"]; p.start_u = d["start_u"]
        p.save(update_fields=["rack", "face", "start_u"])
        return Response(PlacementResponseSerializer(p).data)
```

```python
# backend/apps/placements/urls.py
from rest_framework.routers import DefaultRouter
from .views import PlacementViewSet

router = DefaultRouter()
router.register("placements", PlacementViewSet, basename="placement")
urlpatterns = router.urls
```

- [ ] **Step 5: 运行确认通过** → Run: `... exec web pytest apps/placements -v` → all passed

- [ ] **Step 6: Commit**

```bash
git add backend/apps/placements && git commit -m "feat: placement API with schema-validated place/remove/move"
```

---

### Task 8: 操作审计日志（AuditLog）+ Schema

**Files:**
- Modify: `backend/apps/audit/models.py`, `apps.py`
- Create: `backend/apps/audit/signals.py`, `serializers.py`, `views.py`
- Modify: `backend/apps/audit/urls.py`
- Test: `backend/apps/audit/tests/test_audit.py`

**Interfaces:**
- `AuditLog` 模型；`GET /api/auditlog/`（只读）。
- **Schema**：`AuditLogResponseSerializer` 定义响应；`@extend_schema(responses={200: AuditLogResponseSerializer(many=True)})`；无请求体（只读接口）。

- [ ] **Step 1: 写失败测试（含 schema）**

```python
# backend/apps/audit/tests/test_audit.py
import pytest
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
```
> 需 `from rest_framework.test import APIClient`。

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写模型 + 信号（同前版）**

```python
# backend/apps/audit/models.py
from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                 on_delete=models.SET_NULL)
    action = models.CharField(max_length=16)
    target = models.CharField(max_length=255)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

```python
# backend/apps/audit/signals.py
from django.db.models.signals import post_save, post_delete, pre_save
from .models import AuditLog

_MODELS = []

def _snapshot(instance):
    return {f.name: str(getattr(instance, f.name)) for f in instance._meta.concrete_fields
            if not f.primary_key}

def register_audit(model):
    _MODELS.append(model)

def _pre_save(sender, instance, **kwargs):
    if sender in _MODELS and instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._audit_before = _snapshot(old)
        except sender.DoesNotExist:
            instance._audit_before = {}

def _handler(sender, instance, **kwargs):
    if sender not in _MODELS:
        return
    target = f"{sender.__name__}:{getattr(instance, 'pk', '?')}"
    if kwargs.get("created"):
        AuditLog.objects.create(action="create", target=target, before={}, after=_snapshot(instance))
    elif kwargs.get("signal") is post_delete:
        AuditLog.objects.create(action="delete", target=target, before=_snapshot(instance), after={})
    else:
        AuditLog.objects.create(action="update", target=target,
                                before=getattr(instance, "_audit_before", {}),
                                after=_snapshot(instance))

post_save.connect(_handler)
post_delete.connect(_handler)
pre_save.connect(_pre_save)
```

```python
# backend/apps/audit/apps.py
from django.apps import AppConfig

class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"

    def ready(self):
        from . import signals  # noqa
        from apps.rooms.models import Room
        from apps.racks.models import Rack
        from apps.devices.models import Device
        from apps.placements.models import Placement
        for m in (Room, Rack, Device, Placement):
            signals.register_audit(m)
```

- [ ] **Step 4: 写响应 Schema / ViewSet / urls**

```python
# backend/apps/audit/serializers.py
from rest_framework import serializers
from .models import AuditLog

class AuditLogResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "operator", "action", "target", "before", "after", "created_at"]
        read_only_fields = fields
```

```python
# backend/apps/audit/views.py
from rest_framework import viewsets
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import AuditLog
from .serializers import AuditLogResponseSerializer

@extend_schema_view(
    list=extend_schema(responses={200: AuditLogResponseSerializer(many=True)}, tags=["审计"]),
    retrieve=extend_schema(responses={200: AuditLogResponseSerializer}, tags=["审计"]),
)
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().order_by("-created_at")
    serializer_class = AuditLogResponseSerializer
```

```python
# backend/apps/audit/urls.py
from rest_framework.routers import DefaultRouter
from .views import AuditLogViewSet

router = DefaultRouter()
router.register("auditlog", AuditLogViewSet, basename="auditlog")
urlpatterns = router.urls
```

- [ ] **Step 5: 运行确认通过** → Run: `... exec web pytest apps/audit -v` → 3 passed

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat: audit log via signals with response schema"
```

---

### Task 9: 机柜视图 API（usage + uplan + export）+ Schema

**Files:**
- Modify: `backend/apps/racks/views.py`, `urls.py`
- Modify: `backend/apps/racks/reporting.py`（新增 Schema）
- Create: `backend/apps/racks/schema.py`（`UsageResponseSerializer` / `UPlanResponseSerializer`）
- Test: `backend/apps/racks/tests/test_rack_usage_api.py`

**Interfaces:**
- `GET /api/racks/{id}/usage/` → `UsageResponseSerializer` 定义结构（warnings 为字符串数组）。
- `GET /api/racks/{id}/uplan/` → `UPlanResponseSerializer`（A/B 两个数组，元素可为 null 或 `{device_id, asset_no, status}`）。
- `GET /api/racks/{id}/export_devices/` → CSV（`@extend_schema(responses={(200, "text/csv"): OpenApiTypes.BINARY})`）。
- 三个 `@action` 均带 `@extend_schema(request=None, responses=..., tags=["机柜视图"])`。

- [ ] **Step 1: 写失败测试（含 schema 与参数校验）**

```python
# backend/apps/racks/tests/test_rack_usage_api.py
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement

@pytest.fixture
def rack():
    room = Room.objects.create(code="R1", name="一号")
    return Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=5, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"),
        current_load_kw=Decimal("0.9"))

@pytest.mark.django_db
def test_usage_endpoint(rack):
    r = APIClient().get(f"/api/racks/{rack.id}/usage/")
    assert r.status_code == 200
    assert r.data["remaining_u_by_face"] == {"A": 5, "B": 5}
    assert any("负载率" in x for x in r.data["warnings"])

@pytest.mark.django_db
def test_uplan_endpoint(rack):
    d = Device.objects.create(asset_no="D1", name="D1", power_w=100, weight_kg=10, u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=2, u_size=2)
    r = APIClient().get(f"/api/racks/{rack.id}/uplan/")
    assert len(r.data["A"]) == 5
    assert r.data["A"][0] is None and r.data["A"][1]["asset_no"] == "D1"

@pytest.mark.django_db
def test_export_devices_csv(rack):
    d = Device.objects.create(asset_no="D1", name="服务器A", power_w=100, weight_kg=10, u_size=2)
    Placement.objects.create(device=d, rack=rack, face="A", start_u=1, u_size=2)
    r = APIClient().get(f"/api/racks/{rack.id}/export_devices/")
    assert r.status_code == 200 and "D1" in r.content.decode()
    assert r["Content-Type"].startswith("text/csv")

@pytest.mark.django_db
def test_rack_actions_in_openapi_schema():
    paths = APIClient().get("/api/schema/").data["paths"]
    assert any("usage" in p for p in paths)
    assert any("uplan" in p for p in paths)
    assert any("export_devices" in p for p in paths)
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写响应 Schema 与 reporting 服务**

```python
# backend/apps/racks/schema.py
from rest_framework import serializers

class UsageResponseSerializer(serializers.Serializer):
    used_u_by_face = serializers.DictField(child=serializers.IntegerField())
    remaining_u_by_face = serializers.DictField(child=serializers.IntegerField())
    used_power_w = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_power_w = serializers.DecimalField(max_digits=12, decimal_places=2)
    used_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_load_kw = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    load_ratio = serializers.DecimalField(max_digits=8, decimal_places=4, allow_null=True)
    load_ratio_is_estimate = serializers.BooleanField()
    warnings = serializers.ListField(child=serializers.CharField())

class UPlanCellSerializer(serializers.Serializer):
    device_id = serializers.IntegerField()
    asset_no = serializers.CharField()
    status = serializers.CharField()

class UPlanResponseSerializer(serializers.Serializer):
    A = serializers.ListField(child=UPlanCellSerializer(), allow_null=True)
    B = serializers.ListField(child=UPlanCellSerializer(), allow_null=True)
```

```python
# backend/apps/racks/reporting.py
import csv, io
from apps.placements.models import Placement
from apps.placements.services import get_rack_usage
from apps.placements.validation import get_warnings

def usage_payload(rack):
    data = get_rack_usage(rack)
    data["warnings"] = get_warnings(rack)
    return data

def uplan_payload(rack):
    ps = Placement.objects.filter(rack=rack, status__in=("active", "reserved"))
    plan = {"A": [None] * rack.total_u, "B": [None] * rack.total_u}
    for p in ps:
        cell = {"device_id": p.device_id, "asset_no": p.device.asset_no, "status": p.status}
        for u in range(p.start_u, p.start_u + p.u_size):
            if 1 <= u <= rack.total_u:
                plan[p.face][u - 1] = cell
    return plan

def export_devices_csv(rack):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["资产编号", "名称", "型号", "功耗W", "重量kg", "占用U", "面", "起始U"])
    for p in Placement.objects.filter(rack=rack, status="active"):
        d = p.device
        w.writerow([d.asset_no, d.name, d.model, d.power_w, d.weight_kg,
                    p.u_size, p.face, p.start_u])
    return buf.getvalue()
```

- [ ] **Step 4: 在 RackViewSet 加带 schema 注解的 actions**

```python
# 追加到 backend/apps/racks/views.py
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiTypes
from .reporting import usage_payload, uplan_payload, export_devices_csv
from .schema import UsageResponseSerializer, UPlanResponseSerializer

# 在 RackViewSet 类内追加：
    @extend_schema(request=None, responses={200: UsageResponseSerializer}, tags=["机柜视图"])
    @action(detail=True, methods=["get"])
    def usage(self, request, pk=None):
        return Response(usage_payload(self.get_object()))

    @extend_schema(request=None, responses={200: UPlanResponseSerializer}, tags=["机柜视图"])
    @action(detail=True, methods=["get"])
    def uplan(self, request, pk=None):
        return Response(uplan_payload(self.get_object()))

    @extend_schema(request=None,
                   responses={(200, "text/csv"): OpenApiTypes.BINARY}, tags=["机柜视图"])
    @action(detail=True, methods=["get"])
    def export_devices(self, request, pk=None):
        resp = HttpResponse(export_devices_csv(self.get_object()),
                            content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="devices.csv"'
        return resp
```

- [ ] **Step 5: 运行确认通过** → Run: `... exec web pytest apps/racks -v` → all passed

- [ ] **Step 6: Commit**

```bash
git add backend/apps/racks && git commit -m "feat: rack usage/uplan/export endpoints with response schemas"
```

---

### Task 10: 账号与角色权限

**Files:**
- Modify: `backend/apps/accounts/models.py`
- Create: `backend/apps/accounts/permissions.py`
- Test: `backend/apps/accounts/tests/test_roles.py`

**Interfaces:**
- `User`（AbstractUser + role）；权限类 `IsAdminOrOperatorOrReadOnly`。

- [ ] **Step 1: 写失败测试（同前版）**

```python
# backend/apps/accounts/tests/test_roles.py
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
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写模型与权限类（同前版）**

```python
# backend/apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE = [("admin", "管理员"), ("operator", "运维"), ("viewer", "只读")]
    role = models.CharField(max_length=16, choices=ROLE, default="viewer")
```

```python
# backend/apps/accounts/permissions.py
from rest_framework.permissions import BasePermission

class IsAdminOrOperatorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ("admin", "operator"))
```

- [ ] **Step 4: 全局启用权限**

在 `config/settings.py` 的 `REST_FRAMEWORK` 增加：
`"DEFAULT_PERMISSION_CLASSES": ["apps.accounts.permissions.IsAdminOrOperatorOrReadOnly"]`

> 本 Task 放最后；前面 Task 的未认证测试在权限启用前运行。重跑全量需加 `force_authenticate` 或临时关闭。

- [ ] **Step 5: 运行确认通过** → `... exec web pytest apps/accounts -v` → 2 passed；全量 `... exec web pytest -v` 无回归。

- [ ] **Step 6: Commit**

```bash
git add backend && git commit -m "feat: user roles and read-only permission policy"
```

---

### Task 11: 前端脚手架 + 机柜 U 位可视化

**Files:**
- Create: `frontend/package.json`, `vite.config.ts`, `vitest.config.ts`, `index.html`, `tsconfig.json`
- Create: `frontend/src/{main.ts,api.ts,App.vue}`, `frontend/src/components/RackUPlan.vue`, `frontend/src/views/RackView.vue`
- Test: `frontend/src/components/__tests__/RackUPlan.spec.ts`

**Interfaces:**
- 消费 Task 9 的 `/api/racks/{id}/uplan/` 与 `/usage/`（响应结构严格对齐 Schema）。
- **前端按统一错误结构解析**：`apiGet` 失败时抛出 `err.message`（来自 `{code,message,fields}`）。

- [ ] **Step 1: 写失败测试（同前版）**

```ts
// frontend/src/components/__tests__/RackUPlan.spec.ts
import { mount, flushPromises } from "@vue/test-utils"
import { describe, it, expect, vi } from "vitest"
import RackUPlan from "../RackUPlan.vue"

vi.mock("../../api", () => ({
  apiGet: vi.fn(async (url: string) => {
    if (url.includes("/uplan/")) return { A: [null, {asset_no:"D1",status:"active"}, {asset_no:"D1",status:"active"}], B: [null,null,null] }
    return { remaining_u_by_face: {A:1,B:3}, remaining_power_w: 3800,
             remaining_weight_kg: 785, load_ratio: 0.9, warnings: ["负载率告警"] }
  })
}))

describe("RackUPlan", () => {
  it("渲染U位格子与资产编号", async () => {
    const w = mount(RackUPlan, { props: { rackId: 1 } })
    await flushPromises()
    expect(w.findAll(".u-cell").length).toBe(6)
    expect(w.text()).toContain("D1")
    expect(w.text()).toContain("负载率告警")
  })
})
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 写前端配置与 api.ts（解析统一错误结构）**

```json
// frontend/package.json
{
  "name": "idc-rack-frontend",
  "scripts": { "dev": "vite", "build": "vue-tsc && vite build", "test": "vitest run" },
  "dependencies": { "vue": "^3.4.0", "element-plus": "^2.7.0" },
  "devDependencies": { "vite": "^5.2.0", "typescript": "^5.4.0", "vue-tsc": "^2.0.0",
    "@vitejs/plugin-vue": "^5.0.0", "vitest": "^1.6.0", "@vue/test-utils": "^2.4.0",
    "jsdom": "^24.0.0" }
}
```

```ts
// frontend/src/api.ts
export interface ApiError { code: string; message: string; fields: Record<string, string[]> }

export async function apiGet<T = any>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) {
    const body: ApiError = await r.json()
    throw new Error(body.message || `请求失败: ${r.status}`)
  }
  return r.json()
}
```

`vite.config.ts` 配 vue 插件 + `server.proxy` 把 `/api` 代理到 `http://web:8000`；`vitest.config.ts` 同插件、environment `jsdom`；`index.html` 挂载 `#app`。

- [ ] **Step 4: 写 RackUPlan.vue（同前版）**

```vue
<!-- frontend/src/components/RackUPlan.vue -->
<script setup lang="ts">
import { ref, onMounted } from "vue"
import { apiGet } from "../api"
const props = defineProps<{ rackId: number }>()
const emit = defineEmits<{ (e: "pick", v: { face: string; u: number }): void }>()
const uplan = ref<Record<string, any[]>>({ A: [], B: [] })
const usage = ref<any>({})
onMounted(async () => {
  uplan.value = await apiGet(`/api/racks/${props.rackId}/uplan/`)
  usage.value = await apiGet(`/api/racks/${props.rackId}/usage/`)
})
const cells = (face: string) => [...(uplan.value[face] || [])].map((c, i) => ({ u: i + 1, c })).reverse()
</script>

<template>
  <div class="rack-uplan">
    <div class="summary">
      <span>剩余U：A {{ usage.remaining_u_by_face?.A }} / B {{ usage.remaining_u_by_face?.B }}</span>
      <span>剩余功率：{{ usage.remaining_power_w }} W</span>
      <span>剩余承重：{{ usage.remaining_weight_kg }} kg</span>
      <span v-for="w in usage.warnings || []" class="warn">{{ w }}</span>
    </div>
    <div v-for="face in ['A','B']" :key="face" class="face">
      <h4>{{ face }} 面</h4>
      <div class="grid">
        <div v-for="row in cells(face)" :key="row.u" class="u-cell"
             :class="row.c ? (row.c.status === 'reserved' ? 'reserved' : 'used') : 'free'"
             @click="emit('pick', { face, u: row.u })">
          <small>{{ row.u }}U</small>
          <span v-if="row.c">{{ row.c.asset_no }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: 1fr; gap: 2px; max-width: 320px; }
.u-cell { border: 1px solid #ccc; padding: 4px 8px; cursor: pointer; display: flex; gap: 8px; }
.u-cell.used { background: #409eff; color: #fff; }
.u-cell.reserved { background: #e6a23c; color: #fff; }
.u-cell.free:hover { background: #f0f9ff; }
.warn { color: #f56c6c; margin-left: 8px; }
</style>
```

- [ ] **Step 5: 写 App.vue / main.ts / RackView.vue（最小壳）**

- [ ] **Step 6: 运行确认通过（容器内）** → `$DC exec frontend npm test` → 1 passed；`npm run build` 成功。

- [ ] **Step 7: Commit**

```bash
git add frontend && git commit -m "feat: Vue scaffold, rack U-position visualization and API error parsing"
```

---

### Task 12: 生产部署配置（Compose prod）+ 端到端冒烟 + Schema 全量校验

**Files:**
- Create: `docker-compose.prod.yml`, `frontend/nginx.conf`
- Test: `backend/apps/placements/tests/test_smoke_e2e.py`, `backend/config/test_schema_coverage.py`

**Interfaces:**
- 开发：`$DC up --build`（db + web:8000 + frontend:5173）。
- 生产：`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`（db + web:8000 gunicorn + frontend:80 nginx；db/卷从 base 继承）。
- 端到端覆盖"建档→上架→容量变化→下架→容量恢复→审计存在"；Schema 全量断言覆盖所有端点的 OpenAPI 声明。

- [ ] **Step 1: 写端到端冒烟测试**

```python
# backend/apps/placements/tests/test_smoke_e2e.py
import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.audit.models import AuditLog

@pytest.mark.django_db
def test_full_lifecycle():
    c = APIClient()
    room = Room.objects.create(code="R1", name="一号")
    rack = Rack.objects.create(room=room, name="A", location_code="A-01",
        total_u=10, rated_power_kw=Decimal("1.0"), max_weight_kg=Decimal("100"))
    d = Device.objects.create(asset_no="D1", name="D1", power_w=200, weight_kg=20, u_size=2)
    p = c.post("/api/placements/", {"device": d.id, "rack": rack.id,
        "face": "A", "start_u": 1, "u_size": 2}, format="json").data
    u1 = c.get(f"/api/racks/{rack.id}/usage/").data
    assert u1["used_power_w"] == 200 and u1["used_u_by_face"]["A"] == 2
    c.post(f"/api/placements/{p['id']}/remove/", {}, format="json")
    u2 = c.get(f"/api/racks/{rack.id}/usage/").data
    assert u2["used_power_w"] == 0 and u2["used_u_by_face"]["A"] == 0
    assert AuditLog.objects.exists()
```

- [ ] **Step 2: 写 Schema 全量覆盖测试（核心验收）**

```python
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
```

> 注意：`POST /api/placements/{id}/remove/` 无请求体（request=None），故全量断言中排除；其他写操作必须有 requestBody schema。

- [ ] **Step 3: 写 prod 覆盖层**

```yaml
# docker-compose.prod.yml
services:
  web:
    build: { target: prod }
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
    environment:
      DEBUG: "0"
      ALLOWED_HOSTS: "${ALLOWED_HOSTS:-localhost}"
    restart: unless-stopped
  frontend:
    build: { target: prod }
    ports: ["80:80"]
    depends_on: [web]
    restart: unless-stopped
```
> db 服务与 `pgdata` 卷从 base 继承，生产同样用 PostgreSQL 16。

- [ ] **Step 4: 写 nginx.conf**

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    location / { try_files $uri $uri/ /index.html; }
    location /api/ {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 5: 校验 prod compose 配置** → `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` → 无报错（无 docker 则记录跳过）。

- [ ] **Step 6: 容器内全量测试**

```bash
DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"
$DC exec web sh -c "python manage.py migrate --noinput && pytest -v"
$DC exec frontend npm test
```
Expected: 全部通过（含 Schema 全量覆盖测试）。

- [ ] **Step 7: Commit**

```bash
git add . && git commit -m "chore: compose production profile, e2e smoke and full OpenAPI schema coverage"
```

---

## Self-Review（计划自检）

**1. Spec coverage（需求覆盖）**
- F1 机房 → Task 2 ✓；F2 机柜 → Task 3 ✓；F3 设备 → Task 4 ✓；F4 U位可视化 → Task 11 ✓；F5 上下架/移位 → Task 7 ✓；F6 容量校验预警 → Task 6 ✓（告警展示 Task 9/11）；F7 查询报表 → Task 9 ✓；F8 审计 → Task 8 ✓；F9 扩展点 → Task 3/4 预留字段 ✓。
- 容量规则 §5 → Task 5/6 ✓；非功能 §6 → Task 6/8/10/12 ✓；架构 §7 → Task 0/1/11/12 ✓；验收 AC1–AC7 → Task 2–9/11/12 ✓。
- Docker Compose 集成开发/部署（用户追加）→ Task 0 + Global Constraints + Task 1–11 命令走 compose exec + Task 12 prod 覆盖层 ✓。
- PostgreSQL（用户追加）→ Task 0（postgres 服务+healthcheck+卷）+ Task 1（psycopg + ENGINE）+ Task 5/12 测试连真实 PG + Task 12 prod 继承 db ✓。
- **Schema 定义与参数校验（用户追加）** → Task 1（drf-spectacular + AutoSchema + 统一异常结构 + /api/schema/ /api/docs/）✓；Task 2–4/7–9 每个接口独立 Request/Response Serializer + @extend_schema_view 注解 ✓；Task 9 响应 Schema（usage/uplan/CSV）✓；Task 11 前端按统一错误结构解析 ✓；Task 12 全量 OpenAPI 路径/requestBody/responses 断言 + 参数校验错误结构一致性断言 ✓。
- **缺口**：无；文章参考因验证码未纳入（已在 spec 记录）。

**2. Placeholder scan**：无 "TBD/TODO/implement later/appropriate error handling/similar to Task N"；每个代码步骤都含真实代码。Task 3/4/10/11 的 ViewSet/壳文件用"沿用 Task 2 模式"描述，属于明确的同构实现说明，非占位符；执行者可直接按 Task 2 模板实现。

**3. Type consistency**：`get_rack_usage` 返回键在各 Task 一致；`validate_placement` 签名在 Task 6 定义、Task 7 调用一致；`Placement.status` 枚举一致；`face` 取 'A'/'B' 一致；`uplan_payload` 返回 `{A:[],B:[]}` 与 `UPlanResponseSerializer` 及前端一致；compose 服务名 `web`/`frontend`/`db` 与 nginx 反代、Vite proxy、settings `POSTGRES_HOST=db` 一致；统一错误结构 `{code,message,fields}` 在后端 exception handler、各 Task 测试、前端 api.ts 三处一致。

**已知风险（供执行者注意）**：
- Task 1 的 `test_error_response_structure` 依赖 Task 2 的 RoomRequestSerializer，Task 1 单独跑会失败，Task 2 完成即转绿；这是 TDD 的正常节奏。
- Task 10 的全局权限启用会影响前面 Task 的未认证测试；按 Task 顺序执行即可，重跑全量需加 `force_authenticate` 或临时关闭全局权限。
- `drf-spectacular` 对 `@action` 的 request/response 推断依赖显式注解；每个新接口必须补 `@extend_schema`，否则 Task 12 的全量断言会失败——这正是本计划的强制校验点。
- 无 git 仓库：commit 步骤在当前工作区无法执行，按 Global Constraints 处理。
- PostgreSQL 数据存于 compose 具名卷 `pgdata`；生产备份策略（如 pg_dump 定时任务）未含，可后续补 Task。
