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

健康接口返回 `{"status":"ok","platform":"Runtu Platform"}`（平台名称可配置）；模块接口返回 demo 清单。
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

测试覆盖健康响应、演示清单、自定义模块路由、空模块集、独立应用状态、重复注册拒绝和环境配置。
`backend/modules.py` 定义 ModuleManifest、PlatformModule 协议和内存注册表。模块提供 manifest 与 FastAPI APIRouter，启动时传给 `create_app(modules=[...])`。清单 ID 必须是小写字母开头、后续仅小写字母/数字/下划线，重复 ID 启动失败。模块路由挂在 `/api/modules/<id>`；`GET /api/modules` 列出清单。
默认仅注册无业务逻辑的 DemoModule；不开放远程写入注册接口。注册在工厂启动时完成，后续添加模块应重新创建应用，以确保清单与路由一致。

目前不连接 PostgreSQL，没有 Redis、Docker、登录或服务器安全业务。演示数据随进程退出消失。依赖下载失败应检查网络/平台授权，不要把安装失败视为测试通过。

参考：[FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)、[Vite 指南](https://vite.dev/guide/)。

## TASK-0003 调度核验

2026-10-21 09:07:33.849+08:00 由旧 heartbeat 自动唤醒发现 TASK-0003 v3。
通过原生 automation_update 更新已有 `runtu-github`，未创建第二个任务；工具返回 Updated automation in the app。
随后 view 及配置读回确认为 ACTIVE、`FREQ=MINUTELY;INTERVAL=3`，同一 automation ID；目标聊天、提示词、名称均保留。此处证明更新与持久化成功，不预先声称之后的每次三分钟触发均成功。
