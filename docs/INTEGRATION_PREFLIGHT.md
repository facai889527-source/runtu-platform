# TASK-0008：堆叠 PR 集成预检

核验日期：2026-10-21（Asia/Shanghai），本轮由 10:40:05.393+08:00 heartbeat 自动领取。幂等键 `TASK-0008:8`。以下结论绑定本次 SHA，不保证未来提交后的合并状态。

**结论：未复现 #3 的文件冲突，不提交产品修复。** GitHub 原始响应为 `mergeable=null / mergeable_state=unknown`，而连接器的标准化 PR 响应为 false；不能把后者直接解释为真实冲突。最新 main 与 #3 的本地三方合并干净，隔离合并结果的测试/构建通过。本 PR 仅交付诊断与后续操作建议，不推送、变基或改写 #3/#4/#5。

## 1. 实时状态与基线

已执行 `git fetch origin main` 和 `git fetch origin`。远程分支 SHA 与以下 head 一致；独立报告分支从当前 main `e9b7db1337cd9a45ecebb7f8ad2c025009d55dd7` 创建，base=main。TASK-0008 搜索无既有 PR，本地无同版本执行记录。

约 10:40–10:42+08:00 通过 GitHub 只读接口读取并复核状态：

| PR | 状态 | base / API base SHA | head SHA | 原始 mergeable / mergeable_state |
| --- | --- | --- | --- | --- |
| [#3](https://github.com/facai889527-source/runtu-platform/pull/3) | open，未合并 | main / `d4e379ca25b6f977deb380e92e2c62e41576f24b` | `4c1d1a41e302fde32ed36e0cc11fa8fdc0b98ffa` | 两次读取均 null / unknown |
| [#4](https://github.com/facai889527-source/runtu-platform/pull/4) | open，未合并 | codex/TASK-0003-platform-bootstrap / `4c1d1a41e302fde32ed36e0cc11fa8fdc0b98ffa` | `78ed8591ee12c045524c6120694396ebbbb774a1` | true / clean |
| [#5](https://github.com/facai889527-source/runtu-platform/pull/5) | open，未合并 | codex/TASK-0004-module-core / `78ed8591ee12c045524c6120694396ebbbb774a1` | `641e1428fd400c7b75a79009714cfab07a3f7704` | true / clean |
| [#6](https://github.com/facai889527-source/runtu-platform/pull/6) | open，未合并 | main / `8ea539836830aacc329714da642d22ebcc6a0780` | `0bc79a112d15bf29a89066828814cce7b825a1dd` | 首次 null / unknown，复核 true / clean |
| [#7](https://github.com/facai889527-source/runtu-platform/pull/7) | open，未合并 | main / `2e5976f133d1414d99f13c15969a9862523b0322` | `38fb5b27b2882b716ab937a5ecfa5b5e234245b7` | true / clean |

API 返回的 main base SHA 不全等于当前 main。另以 `/branches/main` 和 fetch 验证最新 main 为 `e9b7db1337cd9a45ecebb7f8ad2c025009d55dd7`，所有本地合并检查均使用它，不能用 API 旧 base 字段冒充最新基线。

## 2. 真实冲突、检查限制与状态计算的区分

[GitHub 官方 REST 文档](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)说明 mergeable 是三态，null 表示后台计算尚未返回结果，应稍后重新读取。本次 #6 从 unknown 变 clean，#3 仍 unknown；历史 false 是否来自同一转换/缓存，未获得服务实现证据，不断言已查明全部历史原因。

本次同时观察到：

- `GET /pulls/3` 原始响应 null/unknown；连接器 `get_pr_info(3)` 标准化快照为 false。两者不等价，报告保留差异，不把缺失值当作文件冲突证据。
- `GET /branches/main`：protected=false；仓库 `/rulesets` 返回空数组。
- #3 head 的 combined commit status 为 pending，但 total_count=0、statuses=[]；对应 Actions runs 为 0。没有观察到失败检查，零检查的 pending 也不是已失败或已通过的 CI。
- 没有读取不可见的组织/管理员策略或穷尽外部 check provider；上述结果不构成可以无审查直接合并的授权。GitHub UI 的最终状态与权限仍须由审查方在合并前确认。

诊断分类：**GitHub 合并元数据尚未给出确定结果；当前没有真实文件冲突或已失败检查的证据。** 没有为了“修复 false”更新依赖、修改产品代码或向父分支制造空提交。

## 3. 本地三方合并证据

Git 版本：2.53.0.windows.3。所有 `git merge-tree --write-tree <left> <right>` 均只写本地 Git 对象，不更新分支/工作树。以下结果均无冲突消息或冲突索引项，命令成功：

| left + right | 合并结果 tree SHA |
| --- | --- |
| 最新 main + #3 head | `87a025f4083d4c75a5c4da89f26dd2df3a036e48` |
| 最新 main + #4 head | `430de07a5c3cb7e16d90c1ce2f88a4b120593e67` |
| 最新 main + #5 head | `0a21fe932d1fd88ae854bce3c7323509c19d3427` |
| 最新 main + #6 head | `358f63bb877db2fbcd6b657682c3a8805276314e` |
| 最新 main + #7 head | `9727e1856c6f7ea0bd02640b5ed37df2405b2811` |
| #3 head + #4 head | `0007cb510c2215f2d80bbb8be44e6ff79d6858e5` |
| #4 head + #5 head | `60b2af4ec09cbeeb4b2b9bcaa16f08dd4385919a` |
| #5 head + #6 head | `c5c6c3de2a79c881d0f8bf4bc56f11126623e3bb` |
| #5 head + #7 head | `983be9664feceb3b35a8acd43cc3ed9f91ab4717` |
| #6 head + #7 head | `2ad743e6fb544c7e09780e6c6fe467954934819f` |

确切冲突文件：**无**。相对共同祖先，main 新增/更新的是 `.coordination/signal.json` 和 TASK-0004 至 TASK-0008 任务文档；#3 新增 FastAPI/Vue/tests/开发指南，并修改 README/.gitignore。两侧没有需要手工裁决的同文件修改，因此没有“选 ours/theirs”的最小修复。

#6 仅新增 docs/CODEX_SKILLS_REVIEW.md，#7 仅新增 docs/CODEX_SKILLS_INSTALL.md；与 main/产品链均可干净合并，二者不是产品依赖。#7 的未安装记录是历史预检结果，后来交互安装成功不改变它当时的事实，本任务不改写其 PR。

## 4. 隔离合并结果验证

使用 `git archive --format=zip --output=<临时归档> <tree SHA>` 加 `Expand-Archive`，把上表 main+#3、main+#5 的实际合并 tree 导出到本地 `.git/codex-coordination/preflight/pr3`、`pr5` 隔离目录。没有 checkout/merge 到任何原 PR 分支；测试目录不会进入本报告提交。

| 验证对象 | Python | 前端 |
| --- | --- | --- |
| main+#3，tree `87a025f...` | `python -m pytest tests -q`：4 passed | `pnpm install --frozen-lockfile --offline` + `pnpm run build`：通过 |
| main+#5（包含 #3/#4/#5），tree `0a21fe9...` | 同命令：22 passed | 同命令：通过 |

Python 来自已有项目 `.venv`（Python 3.14.0），没有重装/改变依赖；`pip check` 为 No broken requirements found。前端使用已有 Node 24.19.0 / pnpm 11.25.0 缓存，35 个包均 reused、downloaded=0，锁文件不变；构建 Vite 7.3.7 / Vue 3.5.44。只在隔离快照安装依赖链接和生成 dist，不复制产品代码到报告 PR。构建工具自身已有 esbuild postinstall 是产品依赖构建步骤，不是第三方 Skill 示例命令。

两组 Python 测试均只有既存 Starlette/httpx TestClient 弃用警告。没有对 #4 单独再跑一次测试；其代码包含在 main+#5 验证中。当前 main/报告分支尚无产品代码，本身不适用业务测试。没有浏览器交互验证或实际 PostgreSQL 在线测试；22 项中的数据库测试使用临时 SQLite，不能推断 PostgreSQL 已通过。

测试/构建通过不代表完整代码审查通过，不替代审查方对公开 API、安全边界和待处理警告的判断。

## 5. 最小处理方案与授权边界

本次最小处理是**保留产品代码不变，提交本报告**。若 GitHub 仍 unknown，由审查方稍后重读原始 `GET /repos/facai889527-source/runtu-platform/pulls/3` 或刷新 UI，核对当前 SHA；没有依据要求把最新 main 合入 #3、重写父分支或把全链代码复制到新 PR。

以下是授权后的操作提纲，**本任务没有执行**：

1. 审查 #3，确认实时 base/head 与检查结果。若仍 unknown，停止合并，先排查 GitHub 计算/接口状态；若状态明确且获用户授权，再由有权限者合并。可优先保留提交祖先关系，减少后续堆叠整理。
2. #3 确认 merged 后，将 #4 的 base 改为 main（例如已安装且授权的 GitHub CLI 中 `gh pr edit 4 --base main`），核对增量仍仅为模块生命周期/详情，重新检查测试。
3. #4 审查合并后，再将 #5 base 改为 main（`gh pr edit 5 --base main`），核对增量仅为持久化，重跑对应测试/构建。
4. 如果 #3/#4 使用 squash 或 rebase merge，先确认原父提交是否仍为 main 祖先；若不在，停止简单重定 base，由审查方授权专门的堆叠整理任务，备份远程 SHA 后只重放子任务增量。当前没有获得改写 #3/#4/#5 的授权，本任务不执行 rebase、force-push 或替换父分支。
5. #6/#7 可独立审查，其文档不阻塞产品链；任何合并仍需正常授权。本报告 PR 也只供审查。

若未来 main 发生新修改，重新 fetch 并重复 merge-tree；只有出现真实冲突才报告确切文件与双方内容，不能沿用本次“无冲突”结论。需要直接更改原 PR、调整 base 或合并时，应请求对应明确授权，不能在报告分支绕过限制。

回滚注意：未合并时撤销 base 调整可恢复到原父分支，先核对其仍存在；不要 reset/强推父分支。已合并变更若需回退，另开经过审查的 revert PR，并按 #5→#4→#3 的依赖反向评估；应用代码回退不等于数据库降级，`downgrade base` 会丢配置数据，不能自动执行。保留审查记录和本次固定 SHA，不因报告或分支清理删除他人工作。

## 6. TASK-0009 管理后台 UI 验收提纲（只规划）

开发起点应为已审查集成的产品链；不要在 main 仍只有协作文件时复制全链实现。正式 TASK-0009 需明确基线 SHA/base。技术保持 Vue 3 + JavaScript、Vite 和现有 API，使用 frontend-design / vue-best-practices 作为参考；Python 测试参考 python-testing-patterns。本任务没有运行 Skill 示例或 find-skills CLI，也不安装其他技能。

建议视觉方向：清晰、紧凑、中文可读的管理工作台。统一 tokens：背景 `#F4F6F8`、表面 `#FFFFFF`、正文 `#182C3A`、主色 `#176B61`、边框 `#D6E0E7`、错误 `#B42318`；后续验证文本对比度后定稿。系统中文字体，无远程字体/素材下载；4/8px 间距刻度、有限圆角、清晰焦点，状态同时用文字而非只靠颜色。

| 验收面 | 可核验行为 |
| --- | --- |
| 布局 | 桌面默认展开侧栏，支持折叠；顶部显示页面标题、状态与刷新动作。移动窄屏导航抽屉可关闭，内容不横向溢出；导航按钮有标签与 aria-expanded。 |
| 导航/组件 | AppShell、SidebarNav、TopBar、DashboardView、ModuleList/Detail 和通用状态提示按职责拆分；组件通信明确，不为小页面增加无必要架构或依赖。 |
| 仪表盘 | 使用 /api/health、/api/modules 的真实数据；区分服务健康与数据库 not_configured/ready/unavailable，不捏造趋势、数量或登录用户。 |
| 模块管理 | 展示分类、enabled/disabled、能力与只读公开配置；禁用模块明确不可操作。不增加未认证的配置写接口。 |
| 异步状态 | 初始加载、刷新中、空列表、失败、重试及数据库503分别可见；失败不展示为“零模块”，刷新不造成竞态覆盖或重复请求。 |
| API 契约 | 保留健康、模块列表和详情契约；兼容无数据库默认模式及持久化错误语义，不通过假数据或假登录掩盖后端限制。 |
| 可访问性 | Tab/Enter/Escape可操作、焦点可见/抽屉关闭后回归触发点、语义标题与实时状态提示；中文长名称/描述及320–375px窄屏、1280px以上桌面有验收。 |
| 验证 | 运行现有后端测试与前端锁定构建；正式授权环境中验证键盘、响应式和加载/空/失败/禁用场景，提供真实截图或记录。未装浏览器工具时报告阻塞，不临时自动安装。 |

不迁移 TypeScript、不引入假登录、无认证写 API、复杂 UI 框架或新业务模块。性能建议不能当作强制重写规则：先对照 Vue 官方资料和可复现测量，再决定是否优化；本次没有实施性能改造。

## 7. 提交边界

原 #3/#4/#5/#6/#7 的远程 head 保持上述 SHA；未推送、改写、关闭、重定 base 或合并。Skills、AGENTS.md、产品依赖与三分钟 ACTIVE heartbeat 均未修改。主工作树已有未跟踪 frontend/node_modules 没有处理或提交。

提交前 `git diff --check`、`git diff --cached --check` 与暂存清单检查；独立 PR 只新增本报告。所有测试临时快照、依赖、构建输出及 Git 元数据均不提交，亦无 .env、IDE 配置、数据库或秘密。
