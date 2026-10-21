# PostgreSQL 验证路径（TASK-0016）

TASK-0017 已取得真实云端证据：[run39547528409](https://github.com/facai889527-source/runtu-platform/actions/runs/39547528409) 三个job全部success，代码head `88dcb8473664afcd1b409477aabadd1484a42160`；Linux普通suite为75 passed/5 skipped，独立PG在线为 **5 passed/0 skipped**，Node12 passed/build成功。实际 Docker28.0.4、PostgreSQL17.11（Debian17.11-1.pgdg12+2），日志确认自建容器删除。详细job链接、image ID与checkout SHA见 [CI_VALIDATION.md](CI_VALIDATION.md)。仍使用原受控 Docker 入口，不接受 service DSN，没有降低护栏或修复生产实现。下文TASK-0016本机阻塞为历史事实；Windows仍无Docker，但不能据此否认本次已完成的云端在线结果。

## TASK-0016 本地环境与阻塞（历史记录）

2026-10-21 Windows 本机检查未发现 docker/podman/psql/postgres/pg_ctl 命令、PostgreSQL/Docker 服务或常见安装目录。因此 **未运行真实 PostgreSQL 在线验证，无 PG 版本或在线通过结果可报告**。没有安装系统服务、调用外部云数据库、探测未知数据库或索取生产凭据。

父提交为 #15 `09379eefa9094b7bbcd5ba3f743c4d2a4797bcfd`，不合入 #13 的独立 CI。任务提供受护栏限制的可重复可选测试路径，不把 SQLite、离线 SQL 或脚本本身的单测当作在线 PG 证据。

## 实施前审查：必须在线验证的风险

已审阅 0001/0002/0003、Database 事务、AuthService session/限流/审计、RBAC 与现有真实 SQLite 测试。

| 风险 | SQLite 与 PG 差异/待验证项 |
| --- | --- |
| 类型/约束 | SQLite 宽松类型、外键通常需显式开启；PG 强类型/外键严格执行，Boolean、VARCHAR 长度、CHECK/UNIQUE 与索引均须核对 |
| 时间 | PG TIMESTAMP WITH TIME ZONE，SQLite 取值常无 tzinfo；服务层按 UTC 解释，PG 会话时区变更仍应得到同一绝对过期语义 |
| 迁移 | PG 原地 ALTER/事务性 DDL 与 SQLite batch 重建不同；0003 必须撤销会话并保留已有身份与密码，不出现匿名授权 |
| 首次引导 | 唯一单例标记与用户名约束应在真实并发事务下最多创建一个 owner；失败事务必须整体回滚 |
| 会话 | PG 真正执行 SELECT FOR UPDATE；用户/会话外键与 ORM flush 顺序、登录轮换删除、禁用与过期均须验证 |
| 限流 | PG ON CONFLICT 与条件 UPDATE 在多连接竞争下不得丢计数/超过配额，数据库故障不能放行 |
| 回滚 | 0003 删除精确角色且保守降权/撤销 session；0002 删除所有认证数据，绝不是无损回滚 |

没有在线证据前不将“看起来兼容”描述为通过。后续命令、安全护栏、测试覆盖与实际执行结果在实现后补充。

## 可选在线入口

仅在**已有、正常授权的本机 Docker Engine 28+ / Linux 容器模式**下，先审查并准备官方 PostgreSQL 17 镜像及现有项目 venv 依赖，再从仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.test_postgres
# 或指定已经审查且本地存在的固定版本/摘要：
.\.venv\Scripts\python.exe -m scripts.test_postgres --image postgres:17.11-bookworm
```

入口默认选择本地 `postgres:17`，先解析成具体 image ID 再创建容器，不会自动 pull、安装 Docker/PG、npm/pip 包或修改 daemon/Windows 安全设置。也接受 `postgres@sha256:...` 官方仓库引用，但会在执行数据库测试前检查实际 PostgreSQL 主版本必须为 17。镜像来源/摘要应由操作者独立审查，本地标签或官方名称本身不是安全证明。本次没有下载镜像。环境中若显式设置 DOCKER_HOST/DOCKER_CONTEXT，会直接拒绝；不会替操作者修改这些设置。

不接受 DSN、数据库名、已有容器 ID、外部端口或生产配置参数。**不要**尝试将 `RUNTU_DATABASE_URL` 或真实连接密码提供给脚本。默认完整 `python -m pytest -q` 会安全跳过五项在线测试；不需要数据库也不失败。可选入口只调用 `tests/postgres`，不会把跳过计为在线通过。

## 隔离与破坏性操作护栏

1. 仅允许 Docker context 的本机 Unix socket 或本机 Windows named pipe，拒绝 TCP/SSH/远程 named pipe；不修改 context。要求 Engine 28+，避免官方说明的旧版本 localhost 端口暴露风险。
2. 脚本生成随机 run ID、唯一 `runtu-pg-...` 容器、`runtu_test_...` 用户/库、随机强密码。凭据只在进程内存/子进程环境中临时注入，不进命令行参数、文件、Git 或输出。Docker 管理员仍可 inspect 容器环境，这是受信任本机管理边界，不是抵御本机管理员的秘密存储。
3. 只发布 `127.0.0.1` 的动态端口，不开放公网；数据目录使用 tmpfs，无 bind mount、外部/生产数据卷，容器资源限额 512MiB/2 CPU。官方 entrypoint 使用密码认证，不允许 trust 配置。该用户在**一次性容器**内具有迁移所需权限，不是生产最小权限配置。
4. 测试前重新 inspect 精确容器 ID、名称、随机所有权 label、运行状态、tmpfs 与唯一 loopback 端口；DSN 必须无 query override、数据库/用户必须与随机 ID 一致。原应用默认 URL 完全不读取，连接后再验证 current_database/current_user。每个测试创建自己唯一的 schema，通过内部生成的 search_path 连接，公共 schema 有未知表即拒绝，不复用其他项目数据。
5. 破坏性 upgrade/downgrade 只在该容器的本测试 schema 内进行。清理前重新验证容器所有权；仅 DROP 本函数确实创建的精确随机 schema，再移除精确 ID 的自建容器及其匿名卷。无 DROP DATABASE、全局 prune、按模糊名称批量删除或外部 DSN 退路。所有权检查失败就停止删除并报告。
6. pytest 子进程输出只在内存捕获，禁用 captured diagnostics 对外显示；入口只输出经过白名单提取的测试计数、失败用例名/源文件行号、非秘密的版本/image ID/容器名。失败不输出 traceback、原始 SQL/DSN/请求体/会话，非法 CLI 参数也不会回显其值。秘密不落原始报告文件。
7. `finally` 尝试清理；若进程被强制结束/主机崩溃，可能留下容器。只根据本次输出的精确 `runtu-pg-<run-id>` 及匹配的 `runtu.pg-validation=<run-id>` label，由操作者审查后清理；不要打印完整 inspect（含临时密码），不要删除不匹配资源。**容器创建、在线验证及真实清理在本机均未执行成功，护栏单测不等于端到端通过。**

loopback 发布仍依赖可信 Docker/主机网络，不隔离同机其他 Docker 管理员或恶意容器；不要在生产 Docker daemon 上运行，也不把它当作插件沙箱。

## 五项在线用例（TASK-0016未执行，TASK-0017云端已通过）

| 用例 | 计划真实验证内容 |
| --- | --- |
| migrations_constraints_legacy_owner_and_lossy_downgrades | 0001→0002→0003；Boolean/默认值/时区列、索引、UNIQUE/CHECK/FK；旧管理员 owner、原 session 撤销、metadata check；降级/重升保守 viewer；0002 降级删除认证数据但保留模块配置 |
| concurrent_bootstrap_exactly_one_owner_and_safe_audit | 多连接并发首次引导只产生一个 owner/标记/审计；失败事务回滚；审计无密码 |
| auth_api_rbac_rotation_csrf_and_disable | 真实 Argon2 登录、轮换、Secure/HttpOnly、三角色矩阵、未知权限403、匿名401、字段白名单；CSRF拒绝、有效退出撤销、禁用立即失效、公共GET；审计无密码/IP原文 |
| atomic_failed_login_window_across_workers | 8 个独立 AuthService 模拟多个 worker，5 次失败与3次限流；PG原子账户/来源计数及失败审计数，避免仅测单进程信号量 |
| same_preauth_session_cannot_login_twice_and_timezone_expiry | 同一预登录 session 并发登录只能轮换成功一次；Asia/Shanghai 连接时区仍正确比较 UTC 到期、撤销过期身份 |

TASK-0016时没有在线证据；TASK-0017首次真实PG执行五项全部通过，没有发现并复现需要修改的生产缺陷，因此**未修改生产认证、RBAC、迁移或前端实现**，更未降低 CSRF/Origin/密码或权限校验。在线通过不等于批准上线，仍需目标环境与生产强化审查。

## TASK-0016 实际执行结果（历史记录）

- Windows / Python 3.14：全量 pytest **69 passed、5 skipped**。原认证/RBAC/SQLite与离线 PG SQL 回归通过；新增护栏测试覆盖外部/默认/错误 DSN、身份不匹配、未知容器、公开端口、持久化挂载、远程 daemon、Docker 缺失、清理所有权拒绝及 CLI 凭据不回显。五项 skipped 全部为在线 PG，用例没有运行。
- 实际执行 `python -m scripts.test_postgres`：**退出码 2**，消息 `Docker unavailable; no PostgreSQL online validation performed`，在数据库连接/容器创建前停止。没有创建数据库/容器，也没有需要清理的测试资源。此结果是阻塞，不是测试通过。
- Node 全量 **12 passed**、pnpm build 成功、git diff --check 通过。前端源码与 #15 相同，没有重复宣称本任务完成新的浏览器/生产验证。原 Starlette/httpx 弃用提示保留，未扩大依赖范围处理。
- 未验证：真实 PG 版本、DDL/并发/FK/锁/时区/鉴权在线结果、Docker 创建/清理端到端路径、实际生产代理与多实例压力、Linux 产品 CI。本 PR 明确保留这些阻塞与风险。

## 生产迁移前必须另行完成

先在具备上述隔离能力的开发/验证环境运行此入口并审查真实结果、记录版本/image ID/所有权清理证据；不要用生产数据库补证。再为实际目标 PG 版本、应用/迁移用户权限、锁等待/超时、负载与维护窗口安排独立演练。固定 PG17 的一次通过不代表其他主版本或生产规模通过。

生产升级必须另外获得批准，备份需加密且保留一致的用户、引导标记、角色、审计和模块配置；先停止应用写入，禁止旧新版本同时迁移。验证恢复及恢复后撤销所有旧 session，避免备份会话复活。

0003 降级会撤销全部 session、丢精确角色，仅 owner 保留旧管理员标记；admin 降级并重升级成为 viewer。0002 降级会删除所有用户/session/审计/限流/引导标记；不能当作无损回滚、密码重置或重新引导捷径。优先审查前向修复或从受控备份恢复，不自动猜测补权，恢复流程仍需单独设计与授权。

TASK-0017选择自建容器路径而非 service DSN，已在独立workflow完成验证，无需合并#13。未来若另行审查一次性PostgreSQL service模式，仍需保留独立测试库/护栏与秘密输出策略，不能直接把 service DSN 注入当前Docker-only入口。本任务**没有修改 #13 workflow、其他 PR、main、signal、AGENTS、Skills 或三分钟自动任务，也未合并/部署。**

参考官方资料：[PostgreSQL 容器变量与临时数据目录](https://hub.docker.com/_/postgres)、[Docker 端口发布与旧版 localhost 风险](https://docs.docker.com/engine/network/port-publishing/)、[PG 约束与外键](https://www.postgresql.org/docs/current/ddl-constraints.html)。
