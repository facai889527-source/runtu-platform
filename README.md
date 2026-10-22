# Runtu Platform

模块化 Python 综合管理平台。未来可扩展服务器安全、域名管理、网站监控、自动化和工具箱等模块。

## 协作

用户 → ChatGPT → GitHub → 本地 Codex。正式任务见 `.coordination/signal.json` 与 `.coordination/tasks/`；开发约定见 [AGENTS.md](AGENTS.md) 和 [协作协议](docs/COORDINATION.md)。

## 本地开发

当前骨架提供 FastAPI 后端、Vue 3 + Vite 前端和内存演示模块。数据库可选；配置后可持久化模块公开配置。
环境：Python 3.12+、Node.js 22.12+、pnpm 11.25.0（可用 `npm install --global pnpm@11.25.0` 安装）。

在仓库根目录的 PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn backend.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

另一个终端启动前端：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

打开终端显示的本地地址（通常为 `http://127.0.0.1:5173`）。
测试和构建：根目录运行 `.\.venv\Scripts\python.exe -m pytest tests -q`；在 frontend 目录运行 `pnpm build`。
详细命令、PyCharm 设置及模块扩展协议见 [开发指南](docs/DEVELOPMENT.md)。

## 可选数据库

默认 `.env.example` 中的 `RUNTU_DATABASE_URL` 为空，可直接启动；健康接口会明确返回 `database=not_configured`。
使用隔离的本地 PostgreSQL 时，将连接 URL 写入本地 `.env` 的 `RUNTU_DATABASE_URL`（驱动为 `postgresql+psycopg`），在根目录执行：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

应用不会自动建表或迁移。配置数据库后连接/必需表不可用时，健康接口返回 HTTP 503，模块详情也不会静默伪装成默认配置。
持久化测试使用临时 SQLite；不代表实际 PostgreSQL 迁移已验证。迁移前请阅读开发指南中的步骤与边界。

## 技术方向

FastAPI、Vue 3；未来计划使用 PostgreSQL（中心）、SQLite（Agent 本地），可选 Linux Agent。本次没有具体业务功能。

> 本仓库为公开仓库，禁止提交密钥、密码、生产环境配置和私人数据。

TASK-0025 增加受控模块启用/禁用及两项公开偏好编辑，仅 owner/admin 的 `module.manage` 权限可写；需先审查并手动执行 `0004_module_management` 迁移，应用不自动迁移。权限矩阵、幂等、审计及回滚边界见 [模块管理说明](docs/MODULE_MANAGEMENT.md)。

## 管理后台

TASK-0036 收紧管理页面与模块元数据认证边界，影响及公开接口例外见 [登录边界](docs/LOGIN_BOUNDARIES.md)。匿名元数据客户端需改用同源认证会话；未配置认证时元数据返回503。

TASK-0034 增加默认关闭、默认需审核的注册策略与只读成员申请基础。仅 owner 可修改策略和批准申请；待审核账户不能登录或通过普通用户编辑绕过审核。需另行审查并授权 `0006_registration_policy` 迁移，安全边界与降级拒绝条件见 [注册策略与审核说明](docs/REGISTRATION.md)。

TASK-0030 用户管理基础的接口、owner 专用权限、自我/最后 owner 保护与密码处理边界见 [用户管理说明](docs/USER_MANAGEMENT.md)。复用现有表，无公开注册或密码重置；本地真实库与服务不会在产品任务中自动修改或重启。

TASK-0031 为显式 `assigned` 业务模块提供用户授权基础与工作台入口，公开 Demo 保持原契约；需审查 `0005_user_module_access` 并另行授权本地迁移后启用。权限矩阵、模块作者接入与范围见 [用户模块授权](docs/USER_MODULE_ACCESS.md)。

TASK-0009 提供浅色中文仪表盘、只读模块管理（搜索、状态筛选、详情）和设置占位；健康/数据库状态来自现有 API，移动端使用导航抽屉。TASK-0014 新增 `/login` 管理员登录、服务端会话和真实身份提示；TASK-0015 增加固定角色授权基础与只读权限摘要。工作台页面及模块元数据现需登录，登录/注册页面、健康探针及 public Demo 业务端点保留公开；受控模块管理写入见上节，尚无其他业务管理写入或动态权限编辑。认证必须显式配置数据库和同源地址，通过受控本地交互命令初始化 owner，默认没有账户。配置及部署限制见 [认证安全说明](docs/AUTH_SECURITY.md)；角色矩阵、模块边界和迁移回滚风险见 [RBAC 设计](docs/RBAC_DESIGN.md)。Windows 启动、测试与原管理后台截图见 [开发指南](docs/DEVELOPMENT.md#管理后台-uitask-0009)。
