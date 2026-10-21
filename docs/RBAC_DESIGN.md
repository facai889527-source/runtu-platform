# 固定角色授权基础（TASK-0015）

## 实现前威胁模型与决策

已审阅 #14 的真实认证模型、会话校验、审计、0002 迁移、FastAPI 依赖、模块挂载及测试。父提交 200ac0ff99b6cc1e1d23dec976c54125c9cca0b2。威胁包括匿名绕过、viewer 越权、旧布尔标记与角色漂移、会话内缓存权限导致降权不生效、未知权限被 owner 通配放行、前端隐藏代替服务端拒绝，以及插件路由覆盖平台管理命名空间。

采用每用户一个持久化固定角色，不增加动态授权编辑 API。owner 拥有全部已知权限，admin 管理模块并读取审计但不能管理用户，viewer 只有平台/模块读取。未知角色/权限默认拒绝，不提供通配权限。匿名能读公共 GET 不代表其拥有任何角色。只新增受保护的 GET /api/admin/me，返回白名单身份、角色与显式权限；不新增审计列表，audit.read 暂为后续受审查能力预留。

0003 将旧 is_admin=true 用户映射为 owner，其他用户为 viewer；本地引导新管理员明确为 owner。角色是后续授权唯一来源，旧布尔列仅作兼容迁移字段，不能绕过角色依赖。每次请求重新从 DB 获取角色与 active，绝不把权限存入 session 或信任浏览器数据。迁移/降级一律撤销所有 session，避免授权模型切换后复用历史会话。

现有平台 API 先注册，模块统一挂载 /api/modules/{id}，模块普通路由不能覆盖 /api/admin。将在模块挂载边界统一拒绝不安全 HTTP 方法，即使插件漏写权限依赖也不能开放写操作；以后开放必须独立任务审查并明确权限/CSRF/审计。**可信进程内 Python 插件不是安全沙箱**：恶意 Python 可访问进程与数据库，不能承诺隔离；不可信插件执行是 blocker，需要进程/凭据隔离设计。公共 metadata GET 保持匿名。

前端只展示服务端白名单角色/权限，保留当前只读说明，不根据 UI 控制授权。身份/角色读取失败不得显示缓存的管理权限。测试将直接请求受保护 API，证明隐藏按钮不是安全边界；继续复用真实 Argon2、session、Origin、CSRF 和 SQLite。

## 固定权限矩阵

| 权限 | owner | admin | viewer | 匿名 |
| --- | --- | --- | --- | --- |
| platform.read | 是 | 是 | 是 | 否 |
| module.read | 是 | 是 | 是 | 否 |
| module.manage | 是 | 是 | 否 | 否 |
| users.manage | 是 | 否 | 否 | 否 |
| audit.read | 是 | 是 | 否 | 否 |

owner 也没有通配权限，新权限必须显式加入固定策略并审查角色矩阵。角色精确匹配，不隐式继承：`require_role('admin')` 不包含 owner；需要两者时明确 `require_role('owner', 'admin')`。空角色列表、未知角色和未知权限始终拒绝。新增用户的 ORM 默认角色仅 viewer，首次交互引导显式 owner；不提供修改角色的 HTTP API、CLI 参数或默认用户。动态角色、多角色、资源级授权、租户隔离、最后一个 owner 保护与恢复流程均未实现，不能对外开放角色修改。

匿名仍可访问原公共 GET，但公共可读是端点契约，不为匿名生成 viewer 身份。`module.manage`、`users.manage`、`audit.read` 当前只是预留授权，不代表平台已经提供相应写操作或审计读取界面。现有 `is_admin` 响应字段由 owner/admin 角色派生，仅为兼容显示；数据库旧布尔列不参与当前权限判定。

## 服务端依赖与只读 API

从 `backend.auth.routes` 导入 `require_permission`、`require_role`，通过 FastAPI `Depends(require_permission('audit.read'))` 或 `Depends(require_role('owner'))` 绑定到未来经审查的路由/路由器。依赖先验证服务器 session、active、绝对/闲置有效期并从数据库读取当前角色，再检查权限；同一 session 降权立即作用于后续请求。

安全上下文有效但无身份/过期/禁用/撤销返回 401；登录但缺少角色/权限返回 403。配置或存储不可用返回 503，绝不降为匿名允许。不匹配 Origin/Host 等请求上下文先返回 403；这优先于身份错误，避免将恶意跨站请求当作普通登录提示。不安全方法还必须通过原 CSRF 校验。错误和身份响应 no-store。

唯一新增生产端点是 `GET /api/admin/me`，依赖 `platform.read`，返回且仅返回：`id`、`username`、`role`、`permissions`（显式排序数组）。不含密码哈希、session、cookie、IP、来源指纹或完整 ORM 对象。没有审计列表；测试专用 `/probe/*` 不在生产 create_app 注册。

前端 `AccessSummary` 只在身份已由服务器确认且请求完成后挂载，独立请求只读端点，展示实际角色和权限名称；切换身份、加载/失败或退出时不显示旧授权。权限错误不伪造 grants，支持重试。前端只是最近一次读取的摘要，不能代替服务端依赖，不存储任何授权/session 到 localStorage。

## 模块与未来管理写边界

核心认证与 admin 路由在插件之前注册。普通 APIRouter 被固定前缀挂载，插件声明 `/api/admin/me` 实际只会得到 `/api/modules/{id}/api/admin/me`，不能覆盖平台的 `/api/admin/me`。测试直接请求两个地址确认这一点。

平台在每个模块 router 外层注入 `module_readonly_boundary`，拒绝 GET/HEAD/OPTIONS 之外的 HTTP 方法，即使已登录 owner 或模块自身忘记授权也不开放写操作。原生命周期测试中的未保护测试 POST 因此从 200 改为 403；禁用模块仍不挂载，返回 404。公共 health/modules/detail 以及已有演示只读行为不变。

这只保证可信插件的 HTTP 注册边界：GET/HEAD/OPTIONS 必须没有业务副作用，不能通过给写处理器换一个 GET 名称绕过规则；插件代码审查仍是必要条件。进程内 Python 能访问全局状态、数据库和 request.app，因此无法隔离恶意插件，WebSocket/其他协议与不可信插件执行也未经批准。**此限制是未来加载不可信插件的 blocker，本任务没有宣称完成插件沙箱。**

将来开放写接口前，必须另行审查并同时满足：明确的资源与权限依赖、会话复核、精确 Origin/Host、CSRF、事务内成功审计与安全失败事件、输入白名单/请求体上限、不回显或记录秘密。当前权限依赖不会自动写业务审计；没有这些配套不能仅移除只读 gate。绝不把 GET 身份查询当作写入批准。

## 0003 升级与回滚

升级前停止应用写入并备份；使用受控迁移账户执行 `python -m alembic upgrade head`。003 先撤销所有 session，再增加角色并将旧 true 映射 owner、false 映射 viewer，施加 NOT NULL/固定枚举 CHECK。保留用户、密码哈希、bootstrap 标记、审计与模块配置；升级后重新登录。SQLite batch 表重建可能需要维护窗口/额外磁盘，不能与旧应用并发运行；应用启动仍不自动迁移。

降级到 `0002_auth_foundation` 会撤销全部 session 并删除角色列。为避免旧 true 标记复活已降权账户，先重写兼容布尔值：**只有 owner 为 true，admin/viewer 都为 false**。因此 admin 在降级及再次升级后保守成为 viewer，精确角色信息不可恢复；需要审查过的角色快照/恢复方案，不允许自动猜测补权。owner 保留旧管理员能力；若已主动降为 viewer，不会因旧布尔值重新升为 owner。再降到 0001 则删除全部认证数据，风险见 AUTH_SECURITY.md。未经单独批准不连接生产库或执行回滚。

SQLite 实测覆盖旧管理员/普通用户与遗留 session 的升级、降级、再次升级以及 metadata 匹配；原密码与身份不被删除。原 PG 离线 SQL 测试通过，但真实 PostgreSQL 在线 DDL/锁/并发迁移、代理 HTTPS 与多实例授权压力均未验证，不能称作生产验证。SQLite 外键策略与 PG 锁等待需在目标环境验证，保留可回滚备份。

## 验证记录（2026-10-21，Windows）

- Python 3.14：44 passed，含原认证安全回归及 owner/admin/viewer 矩阵、401/403、未知权限/角色、角色 CHECK、实时降权、禁用/撤销/过期、升级旧管理员、保守回滚、公共 GET、字段白名单、模块命名空间与统一写 gate。直接 API 的 viewer 写探针/audit.read 探针均被拒绝，不依赖隐藏按钮。
- Node 24：12 passed；pnpm build 成功；git diff --check 通过。没有新增依赖或 Skills。
- Chrome 真实临时数据库/随机账户：桌面与 390px 手机登录后展示服务端 owner 和明确权限，刷新保持，退出移除角色摘要，360px 未登录表单无溢出，密码字段清空、HttpOnly、无 localStorage 仍通过。没有拦截伪造身份。
- 原完整匿名浏览器导航/响应式/焦点/路由与明确布局夹具回归通过。未连接真实 PG、生产或 Linux 产品 CI；Starlette 的现有 httpx 弃用提示仍存在。

无密码/session 的实际截图：[桌面 owner](images/rbac15/owner-desktop.png)、[手机 owner](images/rbac15/owner-mobile-390.png)。复用 AUTH_SECURITY.md 的隔离浏览器夹具命令，测试凭据/数据库/profile 仅在 Git 元数据内，测试结束显式清理，不上传。未修改调度/Skills、旧 PR 或 main，未合并/部署。
