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

## 管理后台

TASK-0009 提供浅色中文仪表盘、只读模块管理（搜索、状态筛选、详情）和设置占位；健康/数据库状态来自现有 API，移动端使用导航抽屉。TASK-0014 新增 `/login` 管理员登录、服务端会话和真实身份提示；公开只读页面仍可匿名访问，尚无 RBAC 或业务管理写入。认证必须显式配置数据库和同源地址，并通过受控本地交互命令初始化管理员，默认没有账户。配置、测试和部署前限制见 [认证安全说明](docs/AUTH_SECURITY.md)。Windows 启动、测试与原管理后台截图见 [开发指南](docs/DEVELOPMENT.md#管理后台-uitask-0009)。
