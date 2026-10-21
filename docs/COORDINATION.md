# ChatGPT ↔ GitHub ↔ Codex 协作协议 v1

用户只与 ChatGPT 沟通。ChatGPT 将任务写入 .coordination/tasks/TASK-XXXX.md，**最后**更新 .coordination/signal.json 发布信号。Codex 从远程 main 获取信号；当 status=ready 且 task_id/version 未处理时，读取任务并执行。

Codex 应在独立分支开发、测试、创建 PR，并在 PR 中反馈 commit SHA、测试证据、风险与阻塞。ChatGPT 审查，用户确认重要变更。禁止自动合并 main 或自动生产部署。

轮询目标为一分钟，但 Codex Windows 桌面应用是否支持一分钟原生定时尚未验证。首次任务负责验证。若不支持，应报告并提出本地桥接方案，不得声称已经自动化。

防重复：task_id + version 唯一；本地持久化执行状态；执行前检查同一任务是否已有 PR；同时只执行一个任务。异常应报告而非标记成功。
