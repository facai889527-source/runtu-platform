# Codex 协作规则

本项目由用户提出需求，ChatGPT 通过 GitHub 发布正式任务，本地 Codex 负责开发、测试、提交 PR。

首次启动：核实 Git remote 和 main，读取 README.md、docs/COORDINATION.md、docs/ARCHITECTURE.md 和 .coordination/signal.json；只有 status=ready 且 task_id 未执行时才读取 task_file。先验证 Codex Windows 桌面应用是否支持每分钟自动任务，不得假称已设置成功。

执行规则：
- 每个任务在独立 codex/<task-id>-<name> 分支进行，提交 PR，不直接修改 main，不自动合并、不自动部署。
- 每次执行先同步 GitHub main，使用 task_id + version 作为幂等键，检查现存 PR 和本地执行记录，避免重复。
- 同时只运行一个任务；执行结果在 PR 中写明提交 SHA、测试结果、风险和阻塞。
- 只操作项目工作区；禁止提交凭据、密钥、真实环境配置、数据库备份及日志。
- 严禁提交 PyCharm 配置：.idea/、*.iml、*.ipr、*.iws；提交前检查 git status 和 git diff --cached --name-only。
- 不清楚任务或没有权限时停止并报告，不自行扩大操作范围。
