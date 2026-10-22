# 管理员认证基础：威胁模型与设计（TASK-0014）

> TASK-0036 契约更新：`GET /api/modules` 与 `GET /api/modules/{id}` 现在要求有效登录。匿名/失效会话返回401，认证未配置返回503；健康、认证/注册必要接口及显式 public 模块业务/示例端点保留原公开行为。下文旧阶段的“公开元数据/匿名工作台”描述仅代表历史实现。详见 [登录边界](LOGIN_BOUNDARIES.md)。


TASK-0015 增量：现已加入固定 owner/admin/viewer 角色和默认拒绝权限依赖，只新增只读 `GET /api/admin/me`，没有动态角色编辑、审计列表或业务写 API。角色矩阵、模块边界、0003 升级/保守回滚及最新 44 Python/12 Node 测试见 [RBAC_DESIGN.md](RBAC_DESIGN.md)。下文保留 TASK-0014 原始威胁模型与历史验证记录；当前部署必须同时遵守 0003 的维护窗口和会话撤销要求。

## 实现前决策

已阅读现有配置、数据库/迁移、模块清单、路由、API client与测试。保留公开health/modules/detail，无业务管理写接口。认证只证明身份，最小require_authenticated/require_admin依赖不构成完整RBAC。父基线为#12 ca77d7b7a4fdc882e9e3de9b40fde80f222c7249，#13不作产品父级。

威胁包括远程密码猜测/用户枚举、登录CSRF、会话固定/窃取、Host/Origin伪造、禁用用户会话残留、初始化竞争、数据库故障时错误放行、请求/日志/审计泄露凭据。边界是浏览器与同源服务、应用与数据库、受控本地操作员。恶意本地主机/数据库管理员、被攻陷的前端/XSS、完整多实例DoS防护不由本阶段保证。

采用固定版本argon2-cffi的Argon2id；参数m=19456KiB、t=2、p=1，随机salt；未知用户用同参数dummy hash校验，错误消息一致。登录验证前以数据库原子计数限制来源及来源+用户名窗口，避免仅进程内限速；不锁死整个账户。仍需边缘限流、代理信任链和多实例PG实测。

采用256位随机服务端session，Cookie HttpOnly/SameSite=Strict/Path=/；数据库仅存session ID的SHA256。预登录匿名session最多10分钟，登录成功轮换ID并撤销旧session，身份会话有绝对/闲置超时；每次认证重新核验用户active。使用标准库HMAC将session随机密钥与固定域分隔消息派生CSRF同步令牌，令牌可由CSRF端点返回，不能逆推出Cookie中的session ID；不实现自制加密算法。CSRF令牌仅用于CSRF校验，身份session不出JSON/localStorage/URL/日志。

auth_origin必须由环境明确设置。HTTPS默认Secure且使用__Host- Cookie；HTTP只在显式允许且origin与实际客户端都为loopback时使用独立开发Cookie，不能通过任意Host或转发头降级。auth接口拒绝不匹配Host/Origin及跨站Fetch Metadata，POST必须Origin与CSRF均匹配。初始GET csrf只建立无权限、限时且限速的匿名安全上下文，GET me只读取身份/会话活跃时间；两者不修改业务资源。登录/登出均需CSRF，使用手动有界JSON解析，避免框架422回显密码输入。

只提供受控本地交互CLI首次创建管理员；同一事务插入唯一引导标记、管理员和审计，标记保留防止删除用户后重新初始化，不提供网络引导/默认凭据。清理过期会话为显式CLI，不自动新增系统定时任务。审计仅事件名、用户ID、来源指纹和UTC时间，不保存密码/Cookie/token/请求体。存储不可用一律安全503，拒绝无法验证的会话。应用启动仍不自动迁移。

本阶段不实现业务写API、角色管理、外部身份服务、密码找回/MFA或生产部署。实现后的命令、验证与部署限制将在下文补充。

## 使用与配置

配置统一使用 `RUNTU_` 环境变量（本地也可使用被 Git 忽略的 `.env`），不得将实际数据库凭据、管理员密码或 session 写入文档或命令行。默认不配置认证，四个认证端点返回安全的 503，匿名原有 GET 契约不变。`/docs`、`/redoc`、`/openapi.json` 默认不可访问；仅隔离开发环境可设 `RUNTU_EXPOSE_API_DOCS=true`，生产保持 false。

| 变量 | 默认值与含义 |
| --- | --- |
| RUNTU_DATABASE_URL | 空；必须指向已显式迁移的隔离数据库 |
| RUNTU_AUTH_ORIGIN | 空；必须是浏览器访问的完整 origin，不能含路径、账号、query 或 fragment |
| RUNTU_AUTH_ALLOW_LOOPBACK_HTTP | false；仅本地 HTTP 调试显式开启，origin 和实际客户端必须是 loopback |
| RUNTU_AUTH_SESSION_SECONDS | 3600；绝对有效期，允许 60–86400 秒 |
| RUNTU_AUTH_IDLE_SECONDS | 900；身份请求间闲置上限，允许 30–3600 秒 |
| RUNTU_EXPOSE_API_DOCS | false；生产不得开启 |

隔离 Windows 本地开发可设置以下非秘密参数；数据库 URL 从受控环境注入，不复制任何生产连接：

```powershell
$env:RUNTU_AUTH_ORIGIN = 'http://127.0.0.1:5173'
$env:RUNTU_AUTH_ALLOW_LOOPBACK_HTTP = 'true'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m backend.auth_cli bootstrap-admin
```

`bootstrap-admin` 只接受交互终端，隐藏输入密码并二次确认；如果无法隐藏输入则拒绝。用户名规范化为小写，3–64 位 `[a-z0-9_.-]`；密码 14–128 字符，操作员应使用密码管理器生成唯一强密码。命令无密码参数、不签发 session、不提供公开注册；数据库唯一引导标记在并发时最多允许一个管理员创建。已有任意用户或引导标记即拒绝；删除用户不会重新开放引导。本阶段不提供恢复命令，禁止手工删除标记作为日常重置流程，恢复方案需另行审查。

前端另开终端 `cd frontend; pnpm dev`。Vite 仅绑定 loopback，代理必须保留原始 Host（本任务显式 `changeOrigin:false`），否则认证拒绝。不要用 `--host 0.0.0.0` 暴露开发服务。HTTP 开发 cookie 名 `runtu_dev_session`，禁止复用到生产；HTTPS 固定使用 `__Host-runtu_session`，Secure 无配置关闭选项。

## API 与扩展边界

| 方法与路径 | 安全边界 |
| --- | --- |
| GET /api/auth/csrf | 无认证也可获取限速、10 分钟匿名 session 的 CSRF proof；不签发身份 |
| GET /api/auth/me | 已认证返回安全用户字段，否则 `authenticated:false,user:null`；存储/配置异常为 503 |
| POST /api/auth/login | 同源 Origin、精确 Host、CSRF、JSON 和有界请求体，失败统一 401 |
| POST /api/auth/logout | 同源与 CSRF 验证后撤销数据库 session 并删除 cookie |

成功/失败认证状态和令牌响应禁止缓存；登录数据使用有界手动解析以避免验证错误回显密码。session ID 只通过 HttpOnly cookie，CSRF proof 只在当前请求内存中；前端不读写 cookie/token 或 localStorage，不增加任何凭据存储。`/me` 刷新活跃时间，未登录不会创建身份。认证状态在页面加载、窗口重新聚焦、可见性恢复、手动刷新和登录/退出后由服务端确认。状态栏是最近一次确认结果，绝不是授权依据；未来写操作必须由服务端重新校验。

`backend.auth.routes.require_authenticated` / `require_admin` 是 FastAPI 依赖：缺少身份默认 401，非管理员默认 403；不安全方法也要求 CSRF。未来审查通过的敏感路由必须显式依赖它们，不能凭前端隐藏按钮或 `is_admin` 字段授权。本阶段只在测试应用注册探针验证边界，不给公共 manifest 或演示模块添加管理写接口；现有第三方模块扩展仍需单独安全审查。

无用户、密码错误和禁用用户用相同错误消息；不存在用户仍做同参数 Argon2id 校验。登录同一来源+用户名最多 5 次/5 分钟，同一来源总共 20 次/5 分钟，成功尝试也计数；CSRF 新建匿名 session 为每来源 30 次/5 分钟。数据库原子 upsert/条件递增共享窗口，拒绝返回 429/Retry-After:300（保守等待）。每进程另有两个同时密码验证槽，超过即拒绝，不能当作完整 DoS 保护。不会信任任意 `X-Forwarded-For` 来分桶；来源指纹为 SHA256(IP)，不是不可逆匿名化承诺。审计记录 bootstrap、login_success、login_failed、logout，尚无完整审计管理/告警；未记录 CSRF 错误请求体。

## 迁移、清理与恢复

`0002_auth_foundation` 在原模块配置表之外增加用户、哈希会话、元信息审计、限流计数和唯一引导标记。包含用户名唯一约束、用户会话关联、到期/审计时间索引；时间统一 UTC。SQLite 返回无时区时间时显式按 UTC 解释；PostgreSQL 使用时区时间列。应用启动不自动迁移。

维护窗口由受控操作员运行（本任务未新增系统/应用定时任务）：

```powershell
.\.venv\Scripts\python.exe -m backend.auth_cli cleanup-sessions
```

清理绝对过期/闲置会话及过期计数；访问无效会话也会撤销，未清理数据不会延长有效期。需按容量/隐私要求制定并审查审计保留和删除策略，当前无自动审计删除。禁用用户后每次身份校验立即拒绝并撤销观察到的 session；受控禁用流程还应在同一事务撤销其全部 session，防止随后重新启用时复用未访问的历史 session。本阶段没有启用/禁用用户的 HTTP 管理接口。

降级到 `0001_module_configs` **删除全部认证用户、会话、审计、限流和引导标记**，不可恢复，不能作为密码重置手段；重新升级不会恢复身份。SQLite 已验证升级/降级及原表保留，尚未连接真实 PostgreSQL。上线前需在隔离 PG 验证 DDL、索引、并发唯一约束/锁、原子限流、回滚和维护窗口；离线 SQL 生成不能替代在线验证。备份需加密、最小权限并覆盖身份与引导标记的一致快照；恢复后应受控撤销所有旧 session，防止备份中会话重新生效。未经审查不回滚/恢复生产库。

## 部署前必做（不代表已获部署授权）

- 取得单独部署批准；完成代码/依赖安全审查。TASK-0015 仅有固定 RBAC 基础，仍未实现完整权限管理、密码找回、MFA、账户管理或业务写 API。
- 配置真实 HTTPS origin，保持 Secure、HttpOnly、SameSite=Strict 和 __Host- 限制，关闭 HTTP 开关与 API docs；不得用浏览器跳过证书错误代替 HTTPS 验证。
- 反向代理严格限制 Host，保留外部规范 Host；仅信任明确列出的代理 IP 的协议/来源头，拒绝任意客户端注入。HTTPS 在代理终止时，ASGI scheme 必须来自可信代理的转发头；本地冒烟禁用代理头信任。不得把 Uvicorn `forwarded-allow-ips=*` 当作便捷修复。
- 采用同源前后端，不启用带凭据的通配 CORS；验证 Origin/Fetch Metadata/CSRF 行为，保持代理/缓存的认证响应 no-store，不记录 Cookie、密码、请求体或 CSRF header。对外启用适当的 CSP/XSS 防护及 TLS/HSTS 策略需按部署另行验证。
- 使用受控交互式初始化、唯一强密码、最小数据库权限；隔离服务与迁移权限。认证依赖固定版本不等于永远安全，更新前审查并测试。
- 在代理/WAF 增加边缘限流、请求体与连接上限，压测实际 Argon2 成本与多 worker 的总资源；数据库窗口计数仅是第一层，当前无分布式总并发预算，也无真实 PG 多实例压测证据。
- 制定 session 清理、审计保留、加密备份、恢复后撤销、监控及故障演练计划，避免存储故障时绕过认证。

## 依赖与许可证

固定版本位于 `backend/requirements-auth.txt`，只增加 Argon2 及其必要底层依赖，无远程身份服务、CDN 或遥测。已检查 PyPI wheel METADATA、依赖声明和许可证，并在项目 venv 离线从已下载 wheel 安装，通过 `pip check`。

| 包 | 固定版本 | 声明 |
| --- | --- | --- |
| argon2-cffi | 25.1.0 | MIT |
| argon2-cffi-bindings | 25.1.0 | MIT；底层 libargon2 上游 CC0-1.0 或 Apache-2.0 |
| cffi | 2.0.0 | MIT，保留 AUTHORS |
| pycparser | 2.23 | BSD-3-Clause |

原 wheel 版权/许可证完整保留（仅规范行尾空白和换行）于 [licenses/auth](licenses/auth)，并补充 [libargon2 原上游声明](licenses/auth/libargon2-LICENSE.txt)。未将库源代码或二进制 wheel 提交仓库。上游来源：[argon2-cffi 25.1.0](https://pypi.org/project/argon2-cffi/25.1.0/)、[bindings 25.1.0 的 MIT 声明](https://github.com/hynek/argon2-cffi-bindings/blob/25.1.0/LICENSE)、[libargon2 20190702 许可证](https://github.com/P-H-C/phc-winner-argon2/blob/20190702/LICENSE)。参数依据 [Argon2 官方 API](https://argon2-cffi.readthedocs.io/en/stable/api.html) 和 [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)；会话/CSRF 边界参考 [Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html) 和 [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)。

本机 Windows/Python3.14 已校验下载 wheel SHA256（这是本次平台产物核验记录，不是所有平台的完整哈希锁）：

```text
argon2-cffi: fdc8b074db390fccb6eb4a3604ae7231f219aa669a2652e0f20e16ba513d5741
argon2-cffi-bindings: a98cd7d17e9f7ce244c0803cad3c23a7d379c301ba618a5fa76a67d116618b98
cffi: 203a48d1fb583fc7d78a4c6655692963b860a417c0528492a6bc21f1aaefab25
pycparser: e5c6e8d3fbad53479cab09ac03729e0a9faf2bee3db8208a550daf5af81a5934
```

## 验证记录（2026-10-21，Windows）

- Python 3.14 `python -m pytest -q`：37 passed，含真实哈希/SQLite、会话、CSRF、Origin/Host、禁用/过期/撤销、并发引导与重复拒绝、限流重置、迁移、交互 CLI 拒绝非 TTY，以及匿名公共 GET。Starlette 提示 TestClient 的 httpx 将弃用，未为消除提示扩大依赖范围。
- Node 24 `node --test tests/*.test.js`：10 passed；`pnpm build` 成功，`pip check` 无冲突。
- 原 `frontend/tests/browser-smoke.mjs` 全部通过：真实匿名 API 与四个屏宽路由/重载/历史/筛选/导航/焦点，以及明确标注的拦截布局夹具，无 JS runtime exception。
- 新 `frontend/tests/auth-browser-smoke.mjs` 使用真实 API 和独立临时 SQLite/随机测试账户：错误密码、字段清空、登录、HttpOnly 不可由 JS 读取、无 localStorage、刷新保持、退出与退出后刷新、390/360 移动表单均通过。未通过拦截伪造登录。初次失败定位为 Vite 改写 Host，保留 Host 后通过；未放宽后端校验。
- 截图在密码字段为空时生成并人工查看，无 session/密码：[桌面](images/auth14/login-desktop.png)、[360 像素](images/auth14/login-mobile-360.png)。
- 未验证：真实 PostgreSQL 在线迁移、多实例压力、生产 HTTPS 代理/证书和 Linux 产品 CI。因此不宣称生产可用或完整权限系统。

复现浏览器认证冒烟需本机 Chrome 和已安装依赖，先启动 Vite，再在根目录显式运行 `python -m tests.serve_auth_smoke`，另一个终端 `node frontend/tests/auth-browser-smoke.mjs`。夹具仅绑定 127.0.0.1，禁用访问日志和代理头信任；临时数据库/随机凭据只在 `.git/codex-coordination/auth14`，正常退出清理数据库与凭据，异常终止后需操作员核对并清理遗留测试文件及专用 Chrome profile，不得上传该目录。本次已执行显式清理。调试期间截图始终先检查密码字段为空；不要将真实管理员账户用于该测试。
