# 本地开发指南

## 环境与 PyCharm

使用 Python 3.12+、Node.js 22.12+（推荐 Node 24 LTS）、pnpm 11.25.0。
本次在 Windows Python 3.14.0、Node 24.19.0、pnpm 11.25.0 验证。
若没有 pnpm，在正常安装了 npm 的终端运行 `npm install --global pnpm@11.25.0`，再运行 `pnpm --version`。

PyCharm 直接打开仓库根目录，项目解释器选择下面创建的 `.venv\Scripts\python.exe`。
所有后端命令的工作目录为仓库根目录，不要在 backend 目录内运行。
无需激活虚拟环境或更改 PowerShell 执行策略。
`.idea/`、`*.iml`、`*.ipr`、`*.iws` 是本地配置，不提交。

## 后端

在仓库根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

已有 `.env` 时跳过复制，避免覆盖本地设置。仅运行服务可安装 `backend/requirements.txt`。
应用工厂在每次创建应用时加载配置：根目录 `.env` 中的 `RUNTU_PLATFORM_NAME` 为平台名称，环境变量优先于文件值。没有配置时默认 Runtu Platform。`.env.example` 只含虚拟值；不要向前端环境变量放入密钥。

另一个根目录终端验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/modules
```

未配置数据库时健康接口返回 `{"status":"ok","platform":"Runtu Platform","database":"not_configured"}`（平台名称可配置）；模块接口返回 demo 清单。原有 status/platform 字段保留。
API 文档为 `http://127.0.0.1:8000/docs`。Ctrl+C 停止服务。

## 前端

保持后端运行，新终端从仓库根目录执行：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

访问终端显示的地址，通常为 `http://127.0.0.1:5173`。页面显示平台名称、后端状态及已注册模块，后端不可用时显示错误并可重试。
Vite 将 `/api` 代理至 `http://127.0.0.1:8000`，本地不需要跨域放行。变更后端端口时同步修改 `frontend/vite.config.js`。

```powershell
pnpm build
pnpm preview
```

构建输出为 frontend/dist（忽略，不提交）。preview 通常使用 `http://127.0.0.1:4173`，同样代理本地后端；仅用于本地验收，不是生产部署。
提交 pnpm-lock.yaml，干净环境使用 frozen-lockfile 安装。pnpm-workspace.yaml 只允许 esbuild 的必需构建脚本。

## 测试与模块扩展

根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

测试覆盖健康响应、演示清单、自定义模块路由、空模块集、独立应用状态、重复注册拒绝、环境配置、禁用路由隔离、只读详情及配置脱敏。
`backend/modules.py` 定义 ModuleManifest、PlatformModule 协议和内存注册表。模块提供 manifest 与 FastAPI APIRouter，启动时传给 `create_app(modules=[...])`。清单 ID 必须是小写字母开头、后续仅小写字母/数字/下划线，最多 64 字符，与数据库主键长度一致；重复 ID 启动失败。模块路由挂在 `/api/modules/<id>`；`GET /api/modules` 列出清单。
默认仅注册无业务逻辑的 DemoModule；不开放远程写入注册接口。注册在工厂启动时完成，后续添加模块应重新创建应用，以确保清单与路由一致。

### 模块生命周期与公开配置

ModuleManifest 保留原有字段，新增可省略的 `category`（默认 null）、`status`（enabled/disabled，默认 enabled）、`capabilities`（字符串能力声明，默认空列表）。能力声明仅是元信息，不构成登录或权限系统。

应用工厂先注册全部清单并校验重复 ID，再仅为 enabled 模块挂载业务路由。disabled 模块仍出现在清单和详情中，但其 GET/POST 等业务路由及 OpenAPI 路径均不挂载。不存在自动启动/停止钩子、热加载、动态 import 或远程执行机制；修改启用状态需重新创建应用。注册时快照元信息，避免后续修改模块实例造成状态漂移。

`GET /api/modules/{id}` 返回清单和 `public_config`；不存在的 ID 返回 404。详情只读，核心详情处理器优先于模块根路由。`GET /api/modules` 仍返回清单数组，原有字段和默认 demo 保持兼容。状态、分类在前端展示，禁用模块保留展示并标明业务路由不可用；空列表与读取失败分别提示。

新模块示例（在服务端源码中静态接入）：

```python
from fastapi import APIRouter
from backend.app import create_app
from backend.modules import ModuleManifest, PublicModuleConfig

class ExampleModule:
    manifest = ModuleManifest(
        id="example", name="Example", version="0.1.0", description="示例",
        category="tools", status="enabled", capabilities=("example:read",),
    )
    router = APIRouter()
    public_config = PublicModuleConfig(
        show_in_navigation=True, refresh_interval_seconds=30,
    )

app = create_app(modules=[ExampleModule()])
```

原有只提供 manifest/router 的 PlatformModule 仍有效；需要公开配置的模块可实现 ConfiguredPlatformModule 协议，提供 public_config。公开配置目前只允许 `show_in_navigation` 布尔值和 `refresh_interval_seconds`（null 或 1–86400 的整数）；未知字段或错误类型在启动时拒绝。该配置只描述模块公开偏好，本页面尚未据此隐藏模块或开启自动刷新。

不要把模块内部 settings、环境变量、数据库配置或 `model_dump()` 全量结果作为公开配置。注册表只读取明确的 public_config，不扫描其他属性；公开模型禁止额外字段，无自由文本/任意字典入口。未来需要新公开字段时，先扩展类型化白名单及脱敏测试，再接入模块。模块自身业务路由仍需各自审查返回值；本协议不为任意开发者代码提供安全沙箱，也未实现用户授权系统。

TASK-0004 的迁移顺序：先审查合并父 PR #3，再把 TASK-0004 PR 的 base 从 `codex/TASK-0003-platform-bootstrap` 调整到 main；若父 PR 被 squash/rebase，需先重放本任务的增量提交并验证 diff。不要自动合并。本次没有修改三分钟调度。

默认不连接数据库，没有 Redis、Docker、登录或服务器安全业务。模块注册表仍在内存中，公开配置可选择持久化。依赖下载失败应检查网络/平台授权，不要把安装失败视为测试通过。

## 可选数据库与迁移（TASK-0005）

数据库 URL 只从本地 `.env` 或环境变量 `RUNTU_DATABASE_URL` 读取；空值表示不启用数据库。Settings 用 SecretStr 避免普通 repr 输出连接信息，不要记录其解密值。不要把真实 URL 提交到仓库。允许的驱动为 `postgresql+psycopg`（目标中心数据库）和 `sqlite`/`sqlite+pysqlite`（开发验证）。

无数据库时服务可启动，详情使用模块默认公开配置；保存操作抛出 DatabaseNotConfiguredError，不伪装为持久化成功。配置数据库后启动仍不自动连接或迁移；健康接口查询必需表的列：可用时 database=ready，不可用或未迁移时 HTTP 503、status=degraded、database=unavailable。ready 只表示本次查询成功，不代表生产可用性或所有未来操作必然成功。详情读取存储失败返回通用 503，不回退到默认值，不返回 URL 或数据库异常详情；清单仍可读取内存元信息。

### 隔离 PostgreSQL 操作步骤

先由操作者准备本机的专用开发数据库与账户（本任务不创建生产数据库），编辑忽略的 `.env`：

```dotenv
RUNTU_DATABASE_URL="postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/runtu_dev"
```

上面只有占位符，需自行替换；密码特殊字符必须 URL 编码。不要复制到 .env.example 或 PR。保持本地数据库服务启动，在仓库根目录执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
```

随后用另一个终端请求 `/api/health`，应返回 database=ready。初始迁移版本为 `0001_module_configs`；`alembic upgrade head` 重复执行不会重复建表。应用本身从不调用 create_all 或自动迁移。`backend/migrations.py` 提供明确的 migrate_database(database) 操作者/测试接口，不在启动时调用。

仅在可丢弃的测试数据库需要回滚时运行 `alembic downgrade base`，该命令会删除模块配置表及其中数据。普通本地启动不需要回滚。更新迁移先在隔离环境验证，禁止自动生产部署。

### SQLite 本地演示与服务层

没有 PostgreSQL 时，可在当前 PowerShell 临时选择忽略的本地 SQLite 文件：

```powershell
$env:RUNTU_DATABASE_URL = 'sqlite:///./local-dev.sqlite3'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
# 服务停止后清除本终端变量，后续可恢复无数据库模式：
Remove-Item Env:RUNTU_DATABASE_URL
```

Python 内部使用 `Database(url)`、`ModuleConfigService(registry, database)`。`load(module_id)` 在没有记录时返回注册时默认值；`save(module_id, PublicModuleConfig(...))` 新建或完整替换该模块的公开配置，提交成功才返回。可传 `create_only=True`，已存在/并发插入冲突时抛 ConfigConflictError，不覆盖已有记录。默认更新是最后提交者覆盖，不提供乐观锁或局部 PATCH。

每个调用使用独立的 session/事务，上下文成功后提交、任何异常回滚并关闭 session；低层 `Database.transaction()` 可用于明确的原子多操作。业务层不直接提交外部传入的 session。存储异常转换为 ConfigStorageError，缺失模块抛 UnknownModuleError；错误配置先校验再写入。没有 HTTP 保存/修改/删除入口，尚无认证授权前不要新增公开写 API。

表 `module_configs` 仅有 module_id（唯一主键）、show_in_navigation（非空、默认 true）、refresh_interval_seconds（可空、1–86400）、updated_at（UTC 更新时间）。配置用明确列而非 JSON/任意字典存储；服务只投影两项公开字段，禁止凭据、token、环境变量入库。Pydantic 已构造的实例也重新验证。数据库约束提供第二层保护。首次插入的更新时间由服务或数据库默认值填充，每次服务保存更新；PostgreSQL 使用带时区时间，SQLite 测试读取时间可能不带时区，按 UTC 理解。

禁用模块的配置保留并可从详情读取，仍不挂载业务路由；模块从注册表移除时数据不自动删除，服务拒绝读取/保存未注册 ID，重新注册后可恢复。没有动态加载或运行任意代码。

### 验证范围与依赖链

根目录运行 `.\.venv\Scripts\python.exe -m pytest tests -q`：测试为临时 SQLite 文件，每次新建并实际执行 Alembic 初始迁移；覆盖升降级/重复迁移、ORM schema 一致性、保存/更新/重新连接、约束与重复键回滚、未知模块、白名单验证、禁用保留、无数据库与缺表的健康状态。测试不使用本地 `.env` 数据库。

本次没有提供或使用隔离 PostgreSQL 服务，**未实际连接 PostgreSQL 或验证其在线迁移**。只额外生成 PostgreSQL 方言的离线迁移 SQL，不能把 SQLite/离线 SQL 通过视为 PostgreSQL 集成测试通过。真实 PostgreSQL 的连接、权限、时区及事务行为仍需在隔离实例上验证。

堆叠依赖链为 **#3 → #4 → #5**。TASK-0005 base 必须为 `codex/TASK-0004-module-core`，只含持久化增量；先审查合并 #3，再逐级调整 #4、#5 的 base。父分支被 squash/rebase 时需由授权操作重放增量并重新检查 diff/测试，不擅自改写父分支。不修改现有三分钟 heartbeat，不自动合并或部署。

参考：[SQLAlchemy 事务/session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)、[Alembic 迁移指南](https://alembic.sqlalchemy.org/en/latest/tutorial.html)。

参考：[FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)、[Vite 指南](https://vite.dev/guide/)。

## TASK-0003 调度核验

2026-10-21 09:07:33.849+08:00 由旧 heartbeat 自动唤醒发现 TASK-0003 v3。
通过原生 automation_update 更新已有 `runtu-github`，未创建第二个任务；工具返回 Updated automation in the app。
随后 view 及配置读回确认为 ACTIVE、`FREQ=MINUTELY;INTERVAL=3`，同一 automation ID；目标聊天、提示词、名称均保留。此处证明更新与持久化成功，不预先声称之后的每次三分钟触发均成功。

## 管理后台 UI（TASK-0009）

本地启动方式见上文：在两个 PowerShell 终端分别启动 FastAPI 与 frontend 下的 `pnpm dev`。
本阶段使用 Vue 3 Composition API + JavaScript，无额外运行依赖。Vite 原有 `/api` 代理保持不变。

- 仪表盘：真实后端健康状态、数据库未配置/可用/不可用说明，以及真实已注册、启用、禁用模块数量。读取失败显示暂不可用，不用零值冒充结果。
- 模块管理：本地名称/ID/分类/描述/能力搜索、状态筛选、只读详情。详情显示 manifest 和 public_config；禁用模块保留展示并说明业务路由不可用。详情 404/503 和网络错误提供重试。
- 设置：明确的未来配置入口占位，尚无认证授权、登录、保存、启用/删除等写操作。
- 桌面侧栏可折叠；760px 及以下为可关闭导航抽屉，支持遮罩、Escape、焦点循环/恢复和背景 inert。刷新读取健康与列表；详情失败时使用详情自己的重新读取操作。
- 不按公开配置隐藏模块或自动轮询。本阶段无持久 URL 路由，刷新浏览器回到仪表盘；不提供暗色主题、真实监控数据或生产部署方案。

### 前端验证

无需安装新的测试框架，在 frontend 目录运行：

```powershell
node --test tests/ui.test.js
pnpm install --frozen-lockfile --offline
pnpm run build
```

`--offline` 只在依赖已经缓存时可用，否则按正常授权联网安装；锁文件不变。
轻量测试覆盖搜索/状态组合、真实 HTTP 状态处理、迟到请求隔离、取消及重试。请求超时 8 秒，重复请求和组件卸载均取消前次请求；generation 校验防止不遵守 abort 的迟到结果覆盖当前视图。

可选 Chrome 冒烟测试：先按上文启动 8000 端口后端和 5173 端口 Vite，再从**仓库根目录**执行：

```powershell
node frontend/tests/browser-smoke.mjs
```

脚本只用 Node 内置模块和现有 Windows Chrome，默认安装位置 `C:/Program Files/Google/Chrome/Application/chrome.exe`。不下载浏览器或第三方包，不关闭浏览器沙箱。9229 调试端口须空闲；使用 `.git/codex-coordination/ui9/chrome-profile` 隔离用户配置，结果截图存于同目录，测试结束关闭自己启动的无头浏览器。不要复用该测试端口运行其他浏览器。截图之前确认本地后端未返回敏感信息。
先验证实际 API，再使用仅在浏览器中的网络拦截夹具验证 ready、降级503、空列表、禁用模块、详情404/503、断网、加载和重试；夹具不写入产品数据或后端。脚本不启动/停止后端与 Vite，测试后在各终端 Ctrl+C。

### 本次实际验证与设计

基线 `641e1428fd400c7b75a79009714cfab07a3f7704`（远程 TASK-0005）。Python 3.14.0、Node 24.19.0、pnpm 11.25.0：22 项后端测试通过（保留既有 Starlette/httpx 弃用警告），4 项 Node 测试通过，锁定离线安装及 Vite 生产构建通过；依赖与锁文件未改。真实 FastAPI + Vite + 现有 Chrome CDP 冒烟通过：1440×1000 桌面、390×844 移动宽度、无横向溢出、搜索筛选、详情、设置、抽屉/Escape，未见运行时异常。异常状态使用显式网络夹具验证，未实际连接 PostgreSQL。未进行完整辅助技术审计或其他浏览器兼容测试。

参考 frontend-design 和 vue-best-practices：统一浅灰画布、深蓝文本、松绿色连接状态，系统中文字体；用连续统计条而非重复装饰卡片承载模块数量。`style.css` 集中颜色/间距/圆角/阴影/交互 tokens 和移动断点，布局组件与 matchMedia 保持同一个 760px 边界。没有采用技能中的 TypeScript 默认建议，也没有根据未经测量的性能断言进行优化。
App 只协调页面和共享只读健康/列表，AppLayout 管理导航及焦点；页面管理本地搜索和详情选择，ModuleDetail 管理独立详情请求，useResource 管理取消/超时/竞态，API client 处理 HTTP 契约，组件通过 props/events 通信。

实际 API 截图（无浏览器夹具）：

![桌面仪表盘](images/task-0009/desktop-dashboard.png)
![手机仪表盘](images/task-0009/mobile-dashboard.png)
![桌面模块详情](images/task-0009/desktop-detail.png)

全部原始截图在本地 `.git/codex-coordination/ui9/`；其中 fixture 前缀图片为测试夹具，未混作实际后端运行证据。下一阶段可在正式任务授权下加入 URL 路由与更完整的浏览器自动化覆盖；认证授权完成前不开放配置写入口。
TASK-0009 PR base 为 `codex/TASK-0005-persistence`，只含本次 UI 增量；原 #3–#8 分支及三分钟自动任务保持原状，不自动合并或部署。
