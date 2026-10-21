# Linux 与 PostgreSQL CI（TASK-0017）

采用路径 A：GitHub 托管 Ubuntu runner 显式 pull 固定摘要官方 PostgreSQL17 镜像，再调用 #16 的自建容器入口。不新增 service DSN 模式，保留唯一测试库/用户、所有权 label、tmpfs、loopback 与清理护栏。#13 独立 CI PR 不合并、不改动。

本任务工作流仅 pull_request，contents:read，checkout 不保留凭据；无 secrets、pull_request_target、部署、SSH、自托管 runner 或写 token。三项独立 job 均超时10分钟，PR并发串行且不取消旧运行。官方 actions 使用与已核验 #13 一致的完整 SHA；Python3.14、Node24、pnpm11.25.0，PG17.11-bookworm 固定 OCI 摘要 bc9388ef9ec36aeadb071135b115108f2efbfc6129306c160dd85eb85af7d571。

Python 全套独立运行，五项在线 PG 默认跳过不视作 PG 通过；PG job 严格要求5 passed/0 skipped，退出码及计数均须成功。测试子进程输出仅内存捕获，对外只打印计数、白名单用例名和文件行号，不回显 traceback/SQL/DSN/密码/session。没有上传原始日志或测试报告附件。Node frozen 安装和 build 后核验锁文件无变化。

镜像摘要来源：[docker-library/repo-info 固定元数据提交](https://github.com/docker-library/repo-info/blob/fb9452dc868ffc0821e92c6b416df1abd81bffb3/repos/postgres/remote/17.11-bookworm.md)，运行时解析并输出实际本地 image ID 与 PG 版本。应用依赖继承原 requirements 的范围及认证固定版本，本任务未扩大生产依赖。

## 实际云端证据（2026-10-21）

[Run 39547528409](https://github.com/facai889527-source/runtu-platform/actions/runs/39547528409)，pull_request / attempt1，completed / success，05:05:17 UTC完成。

- PR #17 测试 head：`88dcb8473664afcd1b409477aabadd1484a42160`。
- base #16：`6d7db02754435f12a6dfd1db7de78abb60a590e1`。
- checkout 使用 GitHub 临时 PR merge ref（日志 `dd4be22`），是上述 head/base 的测试合成提交；**没有合并 PR 或修改目标分支**。后续只追加本证据文档，生产/测试逻辑不变。

| Job | 实际结果 | 证据 |
| --- | --- | --- |
| Linux Python full suite | success；75 passed / 5 skipped / 0 failed / 0 error；pip check通过 | [job 119048980165](https://github.com/facai889527-source/runtu-platform/actions/runs/39547528409/job/119048980165) |
| Linux Node tests and build | success；12 tests / 12 pass；pnpm frozen安装、build、锁文件不变检查通过 | [job 119048980425](https://github.com/facai889527-source/runtu-platform/actions/runs/39547528409/job/119048980425) |
| PostgreSQL online | **success；5 passed / 0 skipped / 0 failed / 0 error**；所有权校验和容器清理完成 | [job 119048980396](https://github.com/facai889527-source/runtu-platform/actions/runs/39547528409/job/119048980396) |

普通 suite 的5 skipped只是避免在无专用入口时连库，不参与在线通过计数。PG job 日志实际输出：

```text
Docker Engine: 28.0.4
local image ID: sha256:e4bdd2f9eeabc0f516e1fa42c4acea97ae571f20877982ac082921b205a52618
Disposable online environment: postgres (PostgreSQL) 17.11 (Debian 17.11-1.pgdg12+2)
pytest counts: passed=5, failed=0, skipped=0, error=0
Owned disposable PostgreSQL container removed.
```

首次新增 PR workflow 正常触发，未因父分支没有工作流或 #16 为 draft 而阻塞；仓库连接已能推送本任务分支、创建PR及读取run/job/log，无需修改main、合并#13或提升workflow权限。#13 原 run39541549106 仅layout成功/产品jobs跳过，不能与本次产品在线成功混淆。没有更改其他PR的draft状态或base。

## 解释与限制

在线五项实际覆盖逐级迁移/约束/legacy owner/会话撤销/有损降级再升级、并发引导、真实认证/RBAC/CSRF/禁用、8个独立服务实例的失败限流原子性、预登录session竞争与非UTC会话时区过期。这次没有在线失败或需要修复的生产方言/并发缺陷；不为制造补丁而修改已有安全机制。

这证明一次 GitHub托管 Ubuntu24.04 / PG17.11 上的小规模集成兼容性，不证明长期多进程/多主机压力、其他PG主版本、最小生产DB权限、生产HTTPS代理/CORS/CSP、备份恢复/灾备或插件隔离。并发测试是单runner上独立 AuthService/多连接，不是完整分布式部署演练。尚未部署生产或开放管理写API。

Windows本地仍没有Docker，不能说已补齐本地PG运行能力。后续head的实际checks与运行链接可直接从PR #17读取；本节精确绑定上面已完成的代码head，避免把文档更新后的新SHA冒称同一次run验证。
