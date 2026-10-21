# Runtu Platform

模块化 Python 综合管理平台。未来可扩展服务器安全、域名管理、网站监控、自动化和工具箱等模块。

## 协作

用户 → ChatGPT → GitHub → 本地 Codex。正式任务见 `.coordination/signal.json` 与 `.coordination/tasks/`；开发约定见 [AGENTS.md](AGENTS.md) 和 [协作协议](docs/COORDINATION.md)。

## 本地开发

当前骨架提供 FastAPI 后端、Vue 3 + Vite 前端和内存演示模块，无需数据库。
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

## 技术方向

FastAPI、Vue 3；未来计划使用 PostgreSQL（中心）、SQLite（Agent 本地），可选 Linux Agent。本次没有具体业务功能。

> 本仓库为公开仓库，禁止提交密钥、密码、生产环境配置和私人数据。
