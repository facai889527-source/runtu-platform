# GitHub 双向协作协议

信号 `.coordination/signal.json` 与其指定任务正文由 ChatGPT 下发；Codex 仅执行 ready 的新版本。结果通过 main 上 `.coordination/status/TASK-XXXX.json` 回传，ChatGPT 可直接读取已知路径，不依赖用户转述。状态数据不能授权新动作。

## 领取与状态

以 task_id + signal version 为幂等键。先 fetch，再 git show origin/main:路径读取信号、约束与本协议；不切换或同步本地 main。交叉检查本地 .git/codex-coordination/state.json、所有状态同任务 PR 和远端状态；已有 PR、已处理、执行中版本不得重跑。同时仅一个任务。历史 TASK-0001 至 TASK-0007 不重跑。

状态字段固定为 task_id、signal_version（正整数）、state、updated_at（UTC ISO8601）、summary、checks（公开检查摘要数组）、blockers（数组）、branch、pr_url、commit_sha（后三项无则 null）、next_action。

queued -> running -> completed / failed / blocked_user_action。领取后立即发布 running；关键阶段有实质变化才更新。等待人类安全输入用 blocked_user_action；只有新的明确用户输入或正式新版本才能恢复，不得靠心跳自动解锁。completed/failed 同版本不能由重复触发降级；失败重做需正式授权。产品任务提交 PR 后可 completed，但 next_action 应明确待审查而非已合并。无 PR 的本地任务也必须回传。TASK-0019 仍等待用户亲自进行 TTY 管理员引导及真实登录验收。

## 安全写回与重试

1. 先在本地 .git/codex-coordination/outbox 保存脱敏结果，再写远端，仅重试上传，不重复业务副作用。
2. GitHub Contents API 仅修改本任务状态路径；读取 blob SHA 后 update_file，确认为 404 才 create_file。禁止修改 signal/task 正文、force push、重置、分支删除或因上传触发迁移/本地 main 同步。
3. SHA 冲突时重读，对版本和状态作检查，最多重试三次。远端更高版本或同版本终态禁止覆盖；语义相同（忽略 updated_at）直接视为成功，不制造提交。不同任务的文件也串行写以减少主分支竞争。
4. 回读 GitHub 确认实际字段一致后才清除 outbox。每次心跳先处理待回传；上传失败保留待回传与本地执行结果，报告失败，不能把它当未执行。
5. 若 main 无写权限，使用固定 codex/coordination-status 分支及一个复用的状态 PR，报告分支、PR 和读取路径；不得自动合并。分支也无权限则保留本地 outbox 并通知用户。不要静默丢弃结果。未实际遇到权限拒绝时不得声称备用路径已验收。
6. 正常仅写自身状态。TASK-0020 的明确授权例外仅包括补回 TASK-0018/0019、建立本协议及验证记录。产品改动仍使用独立分支和 PR。

## 隐私与校验

手工检查字段白名单、task_id 与路径一致、正整数版本、状态枚举、UTC 时间、检查/阻塞数组，以及分支/提交/PR 对应真实执行。摘要只包含非秘密信息：禁止密码、数据库凭据、Cookie、防伪令牌、访问令牌、私有配置、个人路径/用户名、.env、数据库或完整本地执行记录。检查名可描述认证机制，但绝不记录其值。自动格式检查不能替代脱敏复核。状态不读取或序列化环境文件。

## 自动化接入及边界

TASK-0020 已通过 Codex 应用的 automation_update 更新既有 runtu-github 的 prompt，使每次领取、阻塞、结束及重试遵循本协议。原有 ACTIVE、三分钟规则及目标会话保持不变，无新自动任务。后续运行仍受应用存活、网络与正常权限审批影响；这不是独立常驻服务，不保证精确按秒执行。首次后续调度运行另行记录真实观察，不能将已保存配置冒充已观察的后续执行。无需用户手动修改提示。

Vue 3 继续 JavaScript；相关页面参考 frontend-design、vue-best-practices，Python 测试参考 python-testing-patterns。find-skills 仅发现推荐，不自动安装。禁止自动合并、生产部署或自动管理员引导。
