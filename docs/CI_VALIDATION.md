# Linux 与 PostgreSQL CI（TASK-0017）

采用路径 A：GitHub 托管 Ubuntu runner 显式 pull 固定摘要官方 PostgreSQL17 镜像，再调用 #16 的自建容器入口。不新增 service DSN 模式，保留唯一测试库/用户、所有权 label、tmpfs、loopback 与清理护栏。#13 独立 CI PR 不合并、不改动。

本任务工作流仅 pull_request，contents:read，checkout 不保留凭据；无 secrets、pull_request_target、部署、SSH、自托管 runner 或写 token。三项独立 job 均超时10分钟，PR并发串行且不取消旧运行。官方 actions 使用与已核验 #13 一致的完整 SHA；Python3.14、Node24、pnpm11.25.0，PG17.11-bookworm 固定 OCI 摘要 bc9388ef9ec36aeadb071135b115108f2efbfc6129306c160dd85eb85af7d571。

Python 全套独立运行，五项在线 PG 默认跳过不视作 PG 通过；PG job 严格要求5 passed/0 skipped，退出码及计数均须成功。测试子进程输出仅内存捕获，对外只打印计数、白名单用例名和文件行号，不回显 traceback/SQL/DSN/密码/session。没有上传原始日志或测试报告附件。Node frozen 安装和 build 后核验锁文件无变化。

镜像摘要来源：[docker-library/repo-info](https://github.com/docker-library/repo-info/blob/master/repos/postgres/remote/17.11-bookworm.md)，运行时解析并输出实际本地 image ID 与 PG 版本。应用依赖继承原 requirements 的范围及认证固定版本，本任务未扩大生产依赖。

当前仅完成工作流编写，**云端尚未运行，Linux/PG在线结果未验证**；将于创建独立 PR 后核对真实 run URL、job结果、head SHA、版本和在线计数，再补充证据。若 GitHub不触发新增工作流，不修改main、合并#13或提升权限绕过限制，明确报告最小人工步骤。
