# IDC 机柜管理系统

机房/机柜/设备台账、精确 U 位放置与可视化、上下架/移位、容量强校验与负载告警、查询报表、操作审计的一体化 Web 系统。所有 REST 接口的请求/响应参数均由 Schema 显式定义，基于 Schema 自动校验并生成 OpenAPI 文档。

## 技术栈

- **后端**：Python 3.12 · Django 5.0 · Django REST Framework 3.14 · drf-spectacular 0.27（OpenAPI 3.0 Schema）· PostgreSQL 16（psycopg 3）· pytest / pytest-django
- **前端**：Vue 3 · Vite 5 · TypeScript · Element Plus · Vitest · nginx（生产静态服务）
- **环境**：Docker Compose v2（base + dev + prod 三层覆盖），数据库为 compose 内 `postgres:16-alpine` 服务，数据存于具名卷 `pgdata`

## 项目目录结构

```
idc-manager-project/
├── docker-compose.yml            # base 层：db + web + frontend 服务定义
├── docker-compose.dev.yml        # dev 层：源码 bind mount、runserver/vite 热重载、DEBUG=1
├── docker-compose.prod.yml       # prod 层：gunicorn + nginx、restart 策略
├── .env / .env.example           # 环境变量（数据库连接、SECRET_KEY 等；.env 不入库）
├── docs/superpowers/
│   ├── plans/                    # 实施计划（13 个 Task，已全部完成）
│   └── specs/                    # 设计规格说明
├── backend/
│   ├── Dockerfile                # 多阶段（dev / prod）
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── manage.py
│   ├── config/                   # Django 工程配置
│   │   ├── settings.py           # PostgreSQL、DRF、drf-spectacular、权限开关
│   │   ├── urls.py               # 路由 + /api/schema/ + /api/docs/
│   │   ├── exceptions.py         # 统一错误结构 {code, message, fields}
│   │   └── test_*.py             # Schema 全量覆盖等全局测试
│   └── apps/                     # 按领域拆分的 6 个 app
│       ├── rooms/                # 机房台账（模型/Schema/视图/admin）
│       ├── racks/                # 机柜台账 + usage/uplan/export 报表
│       ├── devices/              # 设备台账
│       ├── placements/           # U位放置模型、容量计算、强校验、上下架/移位 API
│       ├── audit/                # 审计日志（signals 自动记录，admin 只读）
│       └── accounts/             # 用户与角色（admin/operator/viewer）权限
└── frontend/
    ├── Dockerfile                # 多阶段（dev / build / prod-nginx）
    ├── nginx.conf                # 生产反代 /api/ 到 web:8000
    └── src/
        ├── api.ts                # fetch 封装，按统一错误结构解析
        ├── App.vue
        ├── components/RackUPlan.vue   # 机柜 U 位图（CSS Grid 自绘）
        ├── views/RackView.vue         # 机柜详情页（下拉选机柜 + U位图）
        └── components/__tests__/      # Vitest 组件测试
```

## 快速开始（开发环境）

```bash
cp .env.example .env

DC="docker compose -f docker-compose.yml -f docker-compose.dev.yml"

$DC up -d --build        # 启动 db + web + frontend
$DC exec web python manage.py migrate    # 首次启动需建表
```

创建管理员账号（交互式输入密码）：

```bash
$DC exec web python manage.py createsuperuser
```

运行测试：

```bash
$DC exec web pytest -v                          # 后端（64 个测试）
$DC exec frontend npm test                      # 前端组件测试
$DC exec frontend npm run build                 # 前端生产构建检查
```

> 注意：后端启用全局权限后，直接跑 pytest 旧回归用例会因未认证 403。全量回归时注入环境变量：`$DC exec -e IDC_DISABLE_PERMISSIONS=1 web pytest -v`（权限类测试本身有 fixture 强制走真实权限类，不受旁路影响）。

## 生产部署

```bash
cp .env.example .env   # 修改 SECRET_KEY、POSTGRES_PASSWORD、ALLOWED_HOSTS

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py migrate --noinput
```

生产架构：web 服务以 gunicorn（3 workers）监听 8000；frontend 服务为 nginx，宿主机 80 端口对外提供静态页面，并将 `/api/` 反向代理到 web:8000；数据库沿用 base 层的 PostgreSQL 16 与 `pgdata` 具名卷。

## 页面与访问入口

| 入口 | 开发环境 | 生产环境 |
|---|---|---|
| 前端页面（机柜 U 位图） | http://localhost:5173/ | http://localhost/（80 端口） |
| Django Admin（数据维护后台） | http://localhost:8000/admin/ | http://localhost:8000/admin/ |
| API 接口文档（Swagger UI） | http://localhost:8000/api/docs/ | http://localhost:8000/api/docs/ |
| OpenAPI Schema（原始 JSON/YAML） | http://localhost:8000/api/schema/ | 同左 |
| DRF API 根 | http://localhost:8000/api/ | 同左 |

默认管理员：`admin / admin123`（首次部署后请立即在 Admin 右上角「修改密码」）。

## 使用方法

### 1. 在 Django Admin 维护数据（推荐入口）

按依赖顺序录入：

1. **机房（Rooms）**：code（限字母/数字/下划线/连字符，如 `R1`）+ 名称
2. **机柜（Racks）**：所属机房、位置编号（唯一，如 `A-01`）、总U数、额定功率（kW）、最大承重（kg）
3. **设备（Devices）**：资产编号（唯一）、名称、功率（W）、承重（kg）、U尺寸（1–10U）
4. **U位放置（Placements）**：选设备 + 机柜 + A/B 面 + 起始U，保存时后端自动执行强校验：
   - U位冲突、超出总U、超出额定功率、超出最大承重 → **直接拦截（400）**
   - 负载率超阈值 → 仅告警不阻断（在前端 U 位图与 usage 接口中展示）
5. **审计（Audit）**：所有增删改操作由 signals 自动写入审计日志，后台只读查看

### 2. 前端 U 位可视化

打开 http://localhost:5173/ ，页面自动加载机柜列表，下拉切换机柜即可查看：

- 每面（A/B）U 位占用状态：蓝色 = 在用，橙色 = 预留，白色 = 空闲
- 剩余U（分面）、剩余功率（W）、剩余承重（kg）与告警信息

## API 接口概览

| 资源 | 路径 | 说明 |
|---|---|---|
| 机房 | `/api/rooms/` | CRUD |
| 机柜 | `/api/racks/` | CRUD |
| 机柜用量 | `/api/racks/{id}/usage/` | 剩余U/功率/承重/负载率/告警 |
| 机柜U位图 | `/api/racks/{id}/uplan/` | A/B 两面逐 U 占用明细 |
| 机柜设备导出 | `/api/racks/{id}/export_devices/` | CSV 导出 |
| 设备 | `/api/devices/` | CRUD |
| 放置 | `/api/placements/` | 上架（POST）、下架（`{id}/remove/`）、移位（`{id}/move/`） |
| 审计日志 | `/api/auditlog/` | 只读查询 |

完整的请求/响应字段定义见 Swagger 文档（http://localhost:8000/api/docs/）。

### 错误响应统一结构

所有接口校验失败返回统一的 400 结构，前端按此解析展示：

```json
{"code": "validation_error", "message": "参数校验失败", "fields": {"字段名": ["错误信息"]}}
```

### 认证与权限

- 认证方式：Session（浏览器登录 Admin 后自动携带）/ Basic
- 角色权限：`admin` / `operator` 可写，`viewer` 只读；未认证用户只读拦截

## 已知范围与扩展预留

- 一期不含 IPAM、动环采集、工单、资产采购报废流程；设备模型已预留 `ip_addresses`、采购/维保日期等扩展字段。
- 生产环境建议补充 `pg_dump` 定时备份策略。
