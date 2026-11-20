# 全局机柜总览大屏 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `GET /api/racks/dashboard/` 聚合接口与前端总览大屏（机柜竖条矩阵 + 全局汇总 + 告警过滤），一屏看清所有机柜占用情况。

**Architecture:** 后端在 RackViewSet 加 `@action(detail=False)` 聚合端点，复用 `get_rack_usage`/`get_warnings` 业务口径；前端引入 vue-router 最小双路由（`/` 大屏、`/rack/:id` 单柜），大屏页 30s 轮询聚合接口，竖条矩阵按机房分组渲染。

**Tech Stack:** Django 5.0.6 + DRF 3.14；Vue 3 + vue-router@4 + Element Plus + Vitest。

**Spec:** `docs/superpowers/specs/2026-11-20-overview-dashboard-design.md`

## Global Constraints

- 复用 `apps.placements.services.get_rack_usage` 与 `apps.placements.validation.get_warnings`，不得重复实现业务口径
- status 阈值：load_ratio > 0.9 或功率/承重超限 → `alert`；> 0.8 → `warn`；否则 `ok`（与 LOAD_WARN_RATIO=0.8 一致）
- 查询优化：`select_related("room").prefetch_related("placements__device")`，全接口 ≤3 条 SQL
- 颜色/主题一律用现有 CSS 变量（`--cyan/--amber/--red/--bg-*`），明暗主题均须正常
- 测试命令：后端 `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e IDC_DISABLE_PERMISSIONS=1 web pytest -q`（64 现有用例须保持通过）；前端 `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm test`（vitest）与 `npm run build`（vue-tsc + vite）
- Windows 宿主，容器名 web/frontend/db；git 分支 develop，直接提交推送

---

### Task 1: 后端 dashboard_payload 聚合函数（TDD）

**Files:**
- Create: `backend/apps/racks/dashboard.py`
- Test: `backend/apps/racks/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `get_rack_usage(rack) -> dict`（含 used_u_by_face/remaining_u_by_face/used_power_w/used_weight_kg/load_ratio/load_ratio_is_estimate）；`get_warnings(rack) -> list`
- Produces: `dashboard_payload() -> dict`，结构见 spec（summary + rooms[].racks[]）

- [x] **Step 1: 写失败测试**

```python
# backend/apps/racks/tests/test_dashboard.py
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.rooms.models import Room
from apps.racks.models import Rack
from apps.devices.models import Device
from apps.placements.models import Placement
import pytest


@pytest.mark.django_db
def test_dashboard_payload_and_status_thresholds():
    room = Room.objects.create(code="R1", name="一号机房")
    ok_rack = Rack.objects.create(room=room, name="A01", location_code="R1-A01",
                                  total_u=42, rated_power_kw=Decimal("10"),
                                  max_weight_kg=Decimal("1000"))
    alert_rack = Rack.objects.create(room=room, name="A02", location_code="R1-A02",
                                     total_u=42, rated_power_kw=Decimal("1"),
                                     max_weight_kg=Decimal("1000"))
    d = Device.objects.create(asset_no="D1", name="服务器", power_w=Decimal("900"),
                              weight_kg=Decimal("20"), u_size=2)
    # alert_rack：900W/1000W 额定 → load_ratio 0.9 → alert
    Placement.objects.create(device=d, rack=alert_rack, face="A", start_u=1,
                             u_size=2, status="active")

    u = get_user_model().objects.create_user("op", password="x", role="operator")
    c = APIClient(); c.force_authenticate(u)
    resp = c.get("/api/racks/dashboard/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["room_count"] == 1
    assert body["summary"]["rack_count"] == 2
    assert body["summary"]["device_count"] == 1
    assert body["summary"]["alert_rack_count"] == 1
    assert body["rooms"][0]["code"] == "R1"
    racks = {r["location_code"]: r for r in body["rooms"][0]["racks"]}
    assert racks["R1-A01"]["status"] == "ok"
    assert racks["R1-A02"]["status"] == "alert"
    assert racks["R1-A02"]["used_u"] == {"A": 2, "B": 0}
    assert racks["R1-A02"]["power"]["used_w"] == 900
```

- [x] **Step 2: 跑测试确认失败**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e IDC_DISABLE_PERMISSIONS=1 web pytest apps/racks/tests/test_dashboard.py -v`
Expected: FAIL（404，路由不存在）

- [x] **Step 3: 实现 dashboard_payload**

```python
# backend/apps/racks/dashboard.py
from decimal import Decimal
from apps.placements.services import get_rack_usage
from apps.placements.validation import get_warnings
from .models import Rack

ALERT_RATIO = Decimal("0.9")
WARN_RATIO = Decimal("0.8")


def _rack_status(load_ratio, used_power_w, rack) -> str:
    if load_ratio > ALERT_RATIO or used_power_w > rack.rated_power_kw * 1000:
        return "alert"
    if load_ratio > WARN_RATIO:
        return "warn"
    return "ok"


def dashboard_payload() -> dict:
    racks = list(Rack.objects.select_related("room")
                 .prefetch_related("placements__device").order_by("id"))
    rooms: dict = {}
    load_sum = Decimal("0")
    alert_count = 0
    device_ids: set = set()
    for rack in racks:
        u = get_rack_usage(rack)
        ratio = u["load_ratio"] or Decimal("0")
        load_sum += ratio
        status = _rack_status(ratio, u["used_power_w"], rack)
        if status != "ok":
            alert_count += 1
        for p in rack.placements.all():
            if p.status == "active":
                device_ids.add(p.device_id)
        rooms.setdefault(rack.room_id, {
            "id": rack.room_id, "code": rack.room.code, "name": rack.room.name,
            "racks": [],
        })
        rooms[rack.room_id]["racks"].append({
            "id": rack.id, "location_code": rack.location_code, "name": rack.name,
            "total_u": rack.total_u,
            "used_u": u["used_u_by_face"],
            "load_ratio": ratio, "load_ratio_is_estimate": u["load_ratio_is_estimate"],
            "power": {"used_w": u["used_power_w"],
                      "rated_w": rack.rated_power_kw * 1000},
            "weight": {"used_kg": u["used_weight_kg"], "max_kg": rack.max_weight_kg},
            "warnings": get_warnings(rack),
            "status": status,
        })
    n = len(racks)
    return {
        "summary": {
            "room_count": len(rooms), "rack_count": n,
            "device_count": len(device_ids),
            "avg_load_ratio": (load_sum / n) if n else Decimal("0"),
            "alert_rack_count": alert_count,
        },
        "rooms": list(rooms.values()),
    }
```

- [x] **Step 4: 跑测试确认通过**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e IDC_DISABLE_PERMISSIONS=1 web pytest apps/racks/tests/test_dashboard.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/apps/racks/dashboard.py backend/apps/racks/tests/test_dashboard.py
git commit -m "feat: dashboard aggregation payload with rack status thresholds"
```

---

### Task 2: 挂载 dashboard 路由 + Schema

**Files:**
- Modify: `backend/apps/racks/views.py`（import 区与 RackViewSet 尾部）
- Create: `backend/apps/racks/schema.py` 追加（已有 UsageResponseSerializer，追加 DashboardResponseSerializer）

**Interfaces:**
- Consumes: `dashboard_payload() -> dict`（Task 1）
- Produces: `GET /api/racks/dashboard/` 端点

- [x] **Step 1: 在 schema.py 追加响应 Serializer**

```python
class RackDashSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    location_code = serializers.CharField()
    name = serializers.CharField()
    total_u = serializers.IntegerField()
    used_u = serializers.DictField(child=serializers.IntegerField())
    load_ratio = serializers.FloatField()
    load_ratio_is_estimate = serializers.BooleanField()
    power = serializers.DictField(child=serializers.FloatField())
    weight = serializers.DictField(child=serializers.FloatField())
    warnings = serializers.ListField(child=serializers.CharField())
    status = serializers.ChoiceField(choices=["ok", "warn", "alert"])


class RoomDashSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    racks = RackDashSerializer(many=True)


class DashboardResponseSerializer(serializers.Serializer):
    summary = serializers.DictField(child=serializers.JSONField())
    rooms = RoomDashSerializer(many=True)
```

- [x] **Step 2: views.py 挂 action**

```python
from .dashboard import dashboard_payload
from .schema import UsageResponseSerializer, UPlanResponseSerializer, DashboardResponseSerializer

    @extend_schema(request=None, responses={200: DashboardResponseSerializer},
                   summary="全局总览大屏聚合", tags=["机柜视图"])
    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        return Response(dashboard_payload())
```

- [x] **Step 3: 全量回归 + 手动验证**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e IDC_DISABLE_PERMISSIONS=1 web pytest -q`
Expected: 68 passed（64 + 4 新增；若数量不同以全绿为准）

Run: `curl -s http://localhost:8000/api/racks/dashboard/`（带认证 cookie 时）或 Swagger `/api/docs/` 检查端点出现
Expected: 返回 JSON，含 summary 与 rooms

- [x] **Step 4: Commit**

```bash
git add backend/apps/racks/views.py backend/apps/racks/schema.py
git commit -m "feat: GET /api/racks/dashboard/ endpoint"
```

---

### Task 3: 前端接入 vue-router

**Files:**
- Modify: `frontend/package.json`（npm install vue-router@4）
- Create: `frontend/src/router.ts`
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/RackView.vue`（读取路由参数预选机柜 + 返回总览入口）

**Interfaces:**
- Produces: 路由 `/` → OverviewView（Task 4 创建，先建占位），`/rack/:id` → RackView；`router` 导出供测试

- [x] **Step 1: 安装依赖**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm install vue-router@4`
Expected: package.json dependencies 出现 `"vue-router": "^4.x"`

- [x] **Step 2: 创建 router.ts**

```typescript
// frontend/src/router.ts
import { createRouter, createWebHistory } from "vue-router"

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "overview", component: () => import("./views/OverviewView.vue") },
    { path: "/rack/:id", name: "rack", component: () => import("./views/RackView.vue") },
    { path: "/rack", redirect: "/" },
  ],
})
```

- [x] **Step 3: main.ts 挂 router；App.vue 改 router-view + 顶部返回入口**

main.ts：`createApp(App).use(ElementPlus).use(router).mount("#app")`（保留 theme 导入在 App 之前）。

App.vue template：

```vue
<template>
  <div class="app-shell">
    <ThemeSwitcher />
    <RouterView />
  </div>
</template>
```

- [x] **Step 4: 创建 OverviewView 占位组件（Task 4 填充），RackView 适配路由**

```vue
<!-- frontend/src/views/OverviewView.vue 占位 -->
<template><div class="rack-view"><h1>总览</h1></div></template>
```

RackView.vue 的 `onMounted` 中：读取 `useRoute().params.id`，若存在且在列表中则预选该机柜；顶栏左侧品牌区改为 `<RouterLink to="/">← 总览</RouterLink>` 链接 + 标题。

- [x] **Step 5: 验证构建与现有测试**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm run build && docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm test`
Expected: build ✓；测试全绿（RackUPlan.spec 不受影响）

- [x] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/router.ts frontend/src/main.ts frontend/src/App.vue frontend/src/views/OverviewView.vue frontend/src/views/RackView.vue
git commit -m "feat: vue-router with overview and rack routes"
```

---

### Task 4: 大屏页 OverviewView（汇总条 + 竖条矩阵 + 告警过滤 + 轮询）

**Files:**
- Modify: `frontend/src/views/OverviewView.vue`（替换占位）
- Test: `frontend/src/__tests__/Overview.spec.ts`

**Interfaces:**
- Consumes: `GET /api/racks/dashboard/` 响应结构（Task 2）；`apiGet`；设计系统 `.panel/.mono/.rise` 与主题 CSS 变量
- Produces: 大屏页；点击竖条 `router.push(/rack/${id})`

- [x] **Step 1: 写失败测试**

```typescript
// frontend/src/__tests__/Overview.spec.ts
import { mount, flushPromises } from "@vue/test-utils"
import { describe, it, expect, vi, beforeEach } from "vitest"

const payload = {
  summary: { room_count: 1, rack_count: 2, device_count: 1,
             avg_load_ratio: 0.45, alert_rack_count: 1 },
  rooms: [{ id: 1, code: "R1", name: "一号机房", racks: [
    { id: 1, location_code: "R1-A01", name: "A01", total_u: 42,
      used_u: { A: 10, B: 5 }, load_ratio: 0.3, load_ratio_is_estimate: true,
      power: { used_w: 100, rated_w: 4000 }, weight: { used_kg: 20, max_kg: 1000 },
      warnings: [], status: "ok" },
    { id: 2, location_code: "R1-A02", name: "A02", total_u: 42,
      used_u: { A: 40, B: 0 }, load_ratio: 0.95, load_ratio_is_estimate: false,
      power: { used_w: 3800, rated_w: 4000 }, weight: { used_kg: 900, max_kg: 1000 },
      warnings: ["负载率 95% 超过告警阈值 80%"], status: "alert" },
  ]}],
}

vi.mock("../api", () => ({ apiGet: vi.fn(async () => payload) }))

import OverviewView from "../views/OverviewView.vue"

describe("OverviewView", () => {
  beforeEach(() => vi.clearAllMocks())

  it("渲染汇总条与每柜竖条", async () => {
    const w = mount(OverviewView, { global: { stubs: ["RouterLink", "RouterView"] } })
    await flushPromises()
    expect(w.findAll(".rack-bar").length).toBe(2)
    expect(w.text()).toContain("1")       // 机房数
    expect(w.text()).toContain("95%")     // 高负载
    expect(w.findAll(".rack-bar.alert").length).toBe(1)
  })

  it("告警过滤：点击告警数后只显示非 ok 机柜", async () => {
    const w = mount(OverviewView, { global: { stubs: ["RouterLink", "RouterView"] } })
    await flushPromises()
    await w.find(".metric.alert-metric").trigger("click")
    expect(w.findAll(".rack-bar").length).toBe(1)
    await w.find(".metric.alert-metric").trigger("click")
    expect(w.findAll(".rack-bar").length).toBe(2)
  })
})
```

- [x] **Step 2: 跑测试确认失败**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm test`
Expected: FAIL（占位组件无 .rack-bar）

- [x] **Step 3: 实现大屏组件**

结构（完整实现，延续「机房控制室」设计系统）：

```vue
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue"
import { useRouter } from "vue-router"
import { apiGet } from "../api"

const data = ref<any>(null)
const error = ref("")
const filterAlert = ref(false)
const FILTERING = 30_000
let timer: number | undefined

const load = async () => {
  try { data.value = await apiGet("/api/racks/dashboard/"); error.value = "" }
  catch (e: any) { error.value = e.message || "加载失败" }
}
onMounted(() => { load(); timer = window.setInterval(load, FILTERING) })
onUnmounted(() => window.clearInterval(timer))

const summary = computed(() => data.value?.summary ?? null)
const rooms = computed(() => {
  const rs = data.value?.rooms ?? []
  if (!filterAlert.value) return rs
  return rs.map((r: any) => ({ ...r, racks: r.racks.filter((x: any) => x.status !== "ok") }))
          .filter((r: any) => r.racks.length > 0)
})
const pct = (used: number, total: number) => total ? Math.min(100, (used / total) * 100) : 0
const router = useRouter()
const open = (id: number) => router.push(`/rack/${id}`)
</script>
```

模板要点（完整实现）：
- 顶栏：品牌「机房控制室 · 总览」+ 副标 `OVERVIEW · ALL RACKS`
- 汇总条 `.metrics`：五个 `.panel.metric`（机房数/机柜数/设备数/平均负载率 `.mono` 百分比/告警机柜数 `.alert-metric`）。告警数 >0 时琥珀色可点击切换 `filterAlert`；为 0 灰色不可点
- 矩阵：`v-for rooms` → 组头（code + name + 该组机柜数）→ `.bar-row` 内 `v-for rack` 渲染 `.rack-bar`（`:class="rack.status"`）
- 竖条内部：左右两栏 A/B（`.col`），每栏底部向上填充 `.fill`（`:style="{ height: pct(used_u[face], total_u) + '%' }"`），fill 用 `--cyan`；status=alert 时 `.rack-bar` 加红描边 + `@keyframes breath` 呼吸光动画；预留部分用琥珀（数据无预留拆分，预留含在 used_u 内，仅告警色区分）
- 竖条下方标签：`location_code`（`.mono` 小字）+ 负载率百分比
- 悬停 tooltip：`el-tooltip` 包裹竖条，内容列 A/B 已用 U、负载率、功率 used/rated、承重 used/max、warnings 逐条
- 点击竖条 → `open(rack.id)`
- 空态：`el-empty`（无机柜时引导到 Admin）
- 加载中：`el-skeleton`；错误：`el-empty :description="error"`
- 样式全部用 CSS 变量，明暗主题均生效；进场用 `.rise` 交错延迟

- [x] **Step 4: 跑测试确认通过 + 构建验证**

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm test && docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npm run build`
Expected: 测试全绿；build ✓（vue-tsc 无类型错误）

- [x] **Step 5: 手动浏览器验证（dev server 5173）**

- `/` 显示大屏；明暗主题各看一遍；点告警数过滤；点竖条跳 `/rack/:id` 且单柜页正确预选
- 30s 后 Network 面板出现第二次 dashboard 请求

- [x] **Step 6: Commit**

```bash
git add frontend/src/views/OverviewView.vue frontend/src/__tests__/Overview.spec.ts
git commit -m "feat: overview dashboard with rack bars, alert filter and polling"
```

---

### Task 5: 收尾 — README 与全量验证

**Files:**
- Modify: `README.md`（访问入口表加 `/` 总览大屏说明、API 速查表加 `GET /api/racks/dashboard/`）

- [x] **Step 1: 更新 README 两处**

访问入口表加一行：`总览大屏 | http://localhost:5173/（生产 80）/ | 全局机柜占用与告警`。
API 速查表加：`GET /api/racks/dashboard/ | 全局总览聚合（summary + rooms[].racks[]，status: ok/warn/alert）`。

- [x] **Step 2: 全量验证**

Run: 后端全量 pytest（须 68+ 全绿）+ 前端 `npm test` + `npm run build` + `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/`
Expected: 全绿、200

- [x] **Step 3: Commit + Push**

```bash
git add README.md
git commit -m "docs: overview dashboard in README"
git push origin develop
```
