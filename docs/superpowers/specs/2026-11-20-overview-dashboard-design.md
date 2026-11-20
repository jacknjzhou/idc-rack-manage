# 全局机柜使用总览大屏 — 设计文档

日期：2026-11-20
状态：已确认（方案 A）

## 目标

新增一个全局总览大屏：一屏看到所有机柜的整体占用情况（U 位、功率、承重、告警），支持从大屏点击进入单柜视图。

## 后端：聚合接口

### 接口

`GET /api/racks/dashboard/` — RackViewSet 上的 `@action(detail=False, methods=["get"])`，由现有 DefaultRouter 自动生成路由，不新增 urls 文件。

### 响应结构

```json
{
  "summary": {
    "room_count": 2,
    "rack_count": 12,
    "device_count": 87,
    "avg_load_ratio": 0.42,
    "alert_rack_count": 3
  },
  "rooms": [
    {
      "id": 1, "code": "BJ-DC1", "name": "北京一号",
      "racks": [
        {
          "id": 5, "location_code": "BJ-DC1-A01", "name": "A01",
          "total_u": 42,
          "used_u": {"A": 30, "B": 12},
          "load_ratio": 0.85, "load_ratio_is_estimate": true,
          "power": {"used_w": 3400, "rated_w": 4000},
          "weight": {"used_kg": 400, "max_kg": 1000},
          "warnings": ["负载率 85% 超过告警阈值 80%"],
          "status": "alert"
        }
      ]
    }
  ]
}
```

### 实现要点

- 复用 `apps.placements.services.get_rack_usage` 与 `apps.placements.validation.get_warnings`，不重复实现业务口径。
- 查询优化：`Rack.objects.select_related("room").prefetch_related("placements__device")`，两次查询完成全部聚合。
- `device_count`：有 active placement 的去重设备数。
- `avg_load_ratio`：各柜 load_ratio 的算术平均（无机柜时为 0）。
- `status` 阈值：load_ratio > 0.9 或功率/承重超限 → `alert`；> 0.8 → `warn`；否则 `ok`。与现有告警阈值（LOAD_WARN_RATIO=0.8）一致。
- 权限沿用全局 `IsAdminOrOperatorOrReadOnly`（GET 只需认证）。

### 新增文件

- `backend/apps/racks/dashboard.py` — `dashboard_payload()` 聚合函数
- `backend/apps/racks/tests/test_dashboard.py` — 测试

## 前端：总览大屏页

### 路由（新增 vue-router）

- 当前项目无路由；引入 `vue-router@4` 最小配置：
  - `/` → `OverviewView.vue`（大屏，新默认首页）
  - `/rack/:id` → `RackView.vue`（现有单柜视图）
  - `/rack` 重定向到 `/`

### 组件

- `src/views/OverviewView.vue` — 大屏主体
- 复用现有设计系统（style.css 的 panel/mono/主题变量），明暗主题均适配
- `RackUPlan.vue` 保留，单柜视图不变

### 视觉与交互

- **顶部汇总条**：五个指标块（机房数/机柜数/设备数/平均负载率/告警机柜数）。告警数为 0 时正常色；>0 时琥珀色且可点击 → 进入告警过滤模式（矩阵只显示 status != ok 的机柜），再点恢复。
- **竖条矩阵**：按机房分组，组头显示机房编号+名称。
  - 每柜一根竖条（高约 160px），内部左右两栏代表 A/B 面，从底部按 `used_u / total_u` 比例填充。
  - 填充色：在用=青色实心；预留=琥珀；告警机柜整条红描边 + 呼吸光动画。
  - 悬停 tooltip：位置编号、A/B 已用 U、负载率、功率、承重、告警列表。
  - 点击竖条 → 跳转 `/rack/:id` 单柜视图。
- 进场动画沿用 `.rise` 交错延迟；数据每 30s 自动刷新。

### 测试（Vitest）

- 竖条渲染数量与机房分组正确
- 告警过滤点击交互
- 汇总条数字渲染

## 不做的事（YAGNI）

- 不做机房平面图/俯视图定位
- 不做实时 WebSocket 推送（30s 轮询足够）
- 不做历史趋势图
- 不做导出
