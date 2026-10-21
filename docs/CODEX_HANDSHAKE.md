# TASK-0001 首次协作握手核验

核验日期：2026-10-21（Asia/Shanghai）。任务幂等键：`TASK-0001:1`。

## 仓库与范围

- 初始工作区不是 Git 仓库，已在其下克隆 `runtu-platform`。
- origin：`https://github.com/facai889527-source/runtu-platform.git`。
- 在 main 执行 `git pull --ff-only origin main`，结果 Already up to date；基线为 `b286e05c69483111da43aadfbf0dfd99950e0d77`。
- 初始工作树干净；完整阅读 AGENTS.md、README.md、docs/COORDINATION.md、docs/ARCHITECTURE.md、signal.json 及 TASK-0001。
- 信号为 ready，task_id=TASK-0001，version=1；GitHub 全状态 PR 搜索 TASK-0001 返回空。
- 使用 `codex/TASK-0001-handshake` 分支，只提交核验文档，不开发业务功能、不合并或部署。

## 一分钟调度：配置成功，实际触发尚未验证

官方文档：https://learn.chatgpt.com/docs/automations?surface=app 。文档说明聊天内任务支持分钟间隔；访问本地文件需要电脑开机、应用运行，任务受沙箱权限约束。文档不是本机持续运行的证据。

实际通过本机应用原生 automation_update 工具创建 heartbeat，返回 Created automation in the app，ID 为 `runtu-github`。读回配置确认：

- kind=heartbeat；status=ACTIVE。
- rrule=`FREQ=MINUTELY;INTERVAL=1`。
- 已绑定当前聊天；提示词要求无新任务保持安静，只处理 ready 的新版本，检查本地状态及现有 PR，单任务串行执行。
- 首次调用缺少目标参数而失败；补充 destination=thread 后成功，未创建重复自动化。

本次交付时未观察到独立的定时触发，未验证连续两次运行、关机恢复或无人值守网络授权。因此只能确认一分钟原生调度被接受且持久化，不能声称每分钟轮询已端到端验证或永久运行。后续第一次实际唤醒应记录时间与远程信号读取结果，必要时补充此 PR。

## 权限与持续运行限制

沙箱内 clone、pull 均遇到 `getaddrinfo() thread failed to start`；申请沙箱外授权后成功。已批准 clone/pull 前缀不等于所有 fetch/push 或无人值守网络操作都已授权。定时运行如无法获取远程信号，应报告阻塞，不能使用缓存冒充新检查。

可行替代：若原生触发不可用，可另行正式下发 Windows 任务计划程序桥接方案，以一分钟间隔只读拉取信号、保存幂等状态并触发受控执行；本任务没有安装该桥接或后台服务。电脑休眠、应用关闭、账户用量和网络权限均可能影响运行，不能保证严格的实时一分钟 SLA。

## 防重复与执行记录

本地持久化状态位于 `.git/codex-coordination/state.json`（Git 元数据，不上传），以 task_id + version 为键。创建 PR 后保存 URL、提交 SHA 和 submitted 状态。每次读取远程 main 信号后，先核对本地记录及 GitHub 所有状态的任务 PR；已有 PR 或已处理版本不再创建 PR。执行中版本不并行重入。新机器没有本地记录时仍须查询 GitHub；异常不得记为成功。

## 验证

- `git remote -v`：fetch/push 均为目标仓库。
- `git pull --ff-only origin main`：成功，main 已同步。
- `git check-ignore .idea/workspace.xml sample.iml sample.ipr sample.iws .env credentials/check.txt`：六项均被忽略。
- 原生 automation_update create/view 与配置读回：一分钟规则已保存为 ACTIVE；实际触发未验证。
- `git diff --check`、`git diff --cached --name-only`、`git status --short`：提交前检查；仅允许本核验文档。
- 没有业务代码或测试套件；不适用业务测试。提交 SHA 和 PR 发布结果见 PR 描述。

剩余限制：首次真实定时触发及持续运行尚无证据；后续无人值守网络权限待实际运行核验。没有向 main 提交开发代码，没有自动合并、部署或提交 IDE 配置、凭据与真实环境数据。
