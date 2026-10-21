# TASK-0006：Codex Skills 盘点与安全评估

调查日期：2026-10-21（Asia/Shanghai）。触发：原生 heartbeat，10:02:34.772+08:00；幂等键 `TASK-0006:6`。
本次仅调查，**没有安装、更新、删除或执行任何第三方 Skill、脚本或安装器**，也没有运行 npx、安装依赖、修改产品代码、AGENTS.md、Skills 目录或三分钟自动化。

## 方法与边界

从远程 main 的 `8ea539836830aacc329714da642d22ebcc6a0780` 新建 `codex/TASK-0006-skills-review`；不继承 #3/#4/#5 的堆叠代码。GitHub 全状态搜索没有既有 TASK-0006 PR，本地状态也没有同版本记录。

只读检查本轮可用 Skills 清单、指定本地目录的文件名与 SKILL.md 元数据；阅读内置安装器说明。通过 GitHub 连接器的 GET 接口读取原始仓库元数据、文件树、SKILL.md、许可证及选定参考文件；网页只采用官方文档和原始作者仓库。没有读取认证配置、Token、数据库凭据或运行候选代码。第三方文档里的“必须执行”指令被当作待审查文本，不作为本轮执行授权。

这是静态适配与风险评估，不是完整安全审计、恶意行为检测或 Windows 安装验收。未展开全部参考文件或 CLI 依赖；没有测试安装后自动发现、重启、浏览器启动或迁移效果。下面的“建议安装”只是下一步建议，仍需单独正式下发安装任务。

## 本机实际清单

本轮上下文暴露且本地对应 SKILL.md 可读的共 18 项：

| 来源 | 本轮可用名称 | 本地核验位置（脱敏） |
| --- | --- | --- |
| 系统 | imagegen、openai-docs、skill-creator、skill-installer | 用户目录下 `.codex/skills/.system/<name>/SKILL.md` |
| bundled 插件 | computer-use:computer-use、visualize:visualize | `.codex/plugins/cache/openai-bundled/` 对应版本目录 |
| primary-runtime 插件 | documents:documents、pdf:pdf、presentations:Presentations、spreadsheets:Spreadsheets、spreadsheets:excel-live-control、template-creator:template-creator | `.codex/plugins/cache/openai-primary-runtime/` 对应版本目录 |
| curated-remote 插件 | plugin-management:plugin-management、sites:sites、sites:sites-remix、work-pets:create-pet、work-pets:pets、work-pets:update-pet | `.codex/plugins/cache/openai-curated-remote/` 对应版本目录 |

另有 `.system/review-agent/SKILL.md` 磁盘文件，元数据为委派场景下的只读缺陷审查；它未出现在本轮可用清单，不能把磁盘存在等同于可直接调用。未为调查启动子代理。

`skill-installer` 已存在，是内置能力，无需再安装。`find-skills` 不在当前清单；只读扫描 `.codex/skills` 和插件缓存中的 SKILL.md 名称也未发现它。用户 `.agents/skills`、仓库及当前工作区父目录的 `.agents/skills` 未发现。结论限于已检查位置，不声称其他用户、管理员目录或其他宿主没有安装。

没有读取完整配置文件，因此未核验所有启停覆盖设置；也没有通过桌面 UI 验证选择器。缓存存在、上下文可用和实际工具授权是不同证据层级，插件能力还可能要求服务连接。

## 机制、安装方法与重启说明

[当前 OpenAI Skills 文档](https://learn.chatgpt.com/docs/build-skills)说明：技能以 SKILL.md 为入口，可附脚本/参考资料；本地发现位置包含仓库和用户 `.agents/skills`，也可经插件分发。当前桌面会话确实提供本地文件路径与内置安装器，证明本机支持该机制；新增第三方技能的实际加载未验证。

[GitHub 上 OpenAI 安装器源码](https://github.com/openai/skills/blob/main/skills/.system/skill-installer/SKILL.md)支持按仓库、子目录或目录 URL 安装，也提供固定 ref 的参数；本机安装器声明默认目标为 `$CODEX_HOME/skills`。这与当前文档的通用发现目录不同，后续应核对实际安装目标/加载结果，不擅自移动系统或插件缓存。

后续获批时，可把已审定的固定提交目录 URL交给内置 `$skill-installer`，或使用其文档中的 `--repo`、`--path`、`--ref`；必须只选单个技能子目录，保留必需 references/许可证，不安装整个插件市场。上述方法仅记录，**本次均未执行**。不要把 Skills CLI 的搜索结果自动变成安装授权。

重启说明有版本差异：

- 当前 OpenAI 文档称会自动发现新增技能，未显示时再重启；本机及当前安装器源码写的是下一轮可用。
- [openai/skills README](https://github.com/openai/skills/blob/main/README.md)仍写安装后重启，但仓库顶部已标记弃用并引向 [openai/plugins](https://github.com/openai/plugins)。不应仅凭这条旧 README 宣称所有版本都必须重启。
- 改动 Codex 配置启停项与单纯新增技能是不同操作；本次未修改配置或重启应用。后续先在下一轮核验，缺失再重启验证，不提前报告安装成功。

[GitHub 官方 Agent skills 文档](https://docs.github.com/en/copilot/concepts/customizations/agent-skills)针对 Copilot，不能用其安装位置、命令或 JetBrains 支持来推断 Codex/PyCharm 的行为。PyCharm 项目能运行也不证明 Codex Skills 已安装。

## 来源快照与维护情况

下表由 GitHub 仓库元数据及 main 提交只读查询得到；时间为 UTC。四仓库均未标记 archived。仓库近期 push 不等于某个技能持续维护或经过安全审查；不以星数/下载量作为推荐依据。

| 原始仓库 | 本次 main 快照提交 | 仓库 pushed_at |
| --- | --- | --- |
| vercel-labs/skills | `a80e4c9d12d607631249d4d7d059f835d4b2f13a` | 2026-10-19 20:34:22Z |
| vuejs-ai/skills | `f5d4b3b869bb8a86ddfea148196f7db64aeefeab` | 2026-10-19 16:17:41Z |
| anthropics/skills | `dbd4588f9e1033efb41dad4bef2f7947c8993d44` | 2026-10-09 18:45:52Z |
| wshobson/agents | `0874a27b17a22e2b7c2e2bcd725768e0803cad06` | 2026-10-19 18:28:14Z |

元数据入口：[Vercel](https://api.github.com/repos/vercel-labs/skills)、[Vue 社区](https://api.github.com/repos/vuejs-ai/skills)、[Anthropic](https://api.github.com/repos/anthropics/skills)、[Seth Hobson](https://api.github.com/repos/wshobson/agents)。固定快照可复核本次阅读内容；未来安装前仍需确认未被撤回或出现新风险。

## 五个候选

### 1. python-testing-patterns — 建议安装（经正式授权后）

- 原始位置：`wshobson/agents` → `plugins/python-development/skills/python-testing-patterns/`；[固定版本 SKILL.md](https://github.com/wshobson/agents/blob/0874a27b17a22e2b7c2e2bcd725768e0803cad06/plugins/python-development/skills/python-testing-patterns/SKILL.md)。来源为社区维护，非 Python/FastAPI 官方团队；维护快照见上表。
- 适用：pytest、fixtures、参数化、mock 和隔离测试；与现有 Python 测试较匹配，可辅助审查回滚/错误场景。不是完整的 FastAPI 安全审计器。
- [仓库许可证](https://github.com/wshobson/agents/blob/0874a27b17a22e2b7c2e2bcd725768e0803cad06/LICENSE)：MIT。该子目录文件树只有 SKILL.md 和两份 Markdown references，没有独立脚本。
- 已读主说明及参考片段；含测试/安装代码示例，使用时可能要求 shell、写测试或新增 pytest-cov/freezegun 等依赖。未发现主说明强制外部服务，不能据此保证所有引用无网络行为。
- 安装前确认：仅此目录、固定提交、保留 MIT 声明；不顺带装整个 agent 市场、依赖或 CI。不照搬旧 ORM/fixture 示例，继续用项目实际版本验证。

### 2. frontend-design — 建议安装（经正式授权后）

- 原始位置：`anthropics/skills` → `skills/frontend-design/`；[固定版本 SKILL.md](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design/SKILL.md)。Anthropic 原始仓库，非 OpenAI 内置；维护快照见上表。
- 适用：管理后台的信息层级、视觉方向、排版与空/失败状态；框架无关，可与 Vue 配合，但不提供 Vue 类型、组件测试或可用性验收保证。
- [目录许可证](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design/LICENSE.txt)：Apache-2.0。目录仅说明与许可证，无脚本；主说明未声明必需网络/MCP。
- 风险：偏重鲜明视觉，可能引发超范围重设计、字体/素材下载或截图请求；现有后台需要稳定易用，不能为风格牺牲中文可读性与键盘操作。
- 安装前确认：只用于正式 UI 任务，保留现有需求与组件栈；素材/浏览器权限另核对，保留许可证，不默认修改产品视觉。

### 3. vue-best-practices — 待确认（技术适配高，规则需审阅）

- 原始位置：`vuejs-ai/skills` → `skills/vue-best-practices/`；[固定版本 SKILL.md](https://github.com/vuejs-ai/skills/blob/f5d4b3b869bb8a86ddfea148196f7db64aeefeab/skills/vue-best-practices/SKILL.md)。Vue 社区来源，不能仅凭组织名视为 Vue 核心团队背书；维护快照见上表。
- 适用：Vue 3、Composition API、SFC、响应性及组件边界，与本项目匹配；不是完整的后台 UX 设计系统。
- [许可证](https://github.com/vuejs-ai/skills/blob/f5d4b3b869bb8a86ddfea148196f7db64aeefeab/LICENSE)：MIT；该目录只有 Markdown 主说明/参考资料，未发现独立脚本。静态读取无需网络服务，后续示例的 fetch/依赖操作仍需任务授权。
- 已检查四份核心参考的结构/相关片段。主说明强推 TypeScript，参考还含将 primitive 值统一改用 shallowRef 的绝对化性能建议；本项目使用 JavaScript，不能把安装变成 TS 迁移或无测量的性能重写。
- 安装前确认：是否接受其默认规则与触发范围，明确保持现有 JS 栈；审完必需 references，核对与 [Vue 官方文档](https://vuejs.org/guide/essentials/reactivity-fundamentals.html)的一致性。该官方页面在本次未进一步读取，因此不将上述性能建议判断为已获官方验证。

### 4. webapp-testing — 待确认（先解决执行与 Windows 边界）

- 原始位置：`anthropics/skills` → `skills/webapp-testing/`；[固定版本 SKILL.md](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/webapp-testing/SKILL.md)。维护快照见上表；[目录许可证](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/webapp-testing/LICENSE.txt)为 Apache-2.0。
- 适用：Python Playwright 对 Vue 页面做真实浏览器验证，框架兼容。目录包含 `scripts/with_server.py` 和三个 examples，本次只阅读，连 `--help` 都未执行。
- [with_server.py](https://github.com/anthropics/skills/blob/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/webapp-testing/scripts/with_server.py)用 shell=True 启动输入命令、探测本地端口并终止直接子进程；Windows 子进程树清理、端口误判与未消费输出管道阻塞需要实测。示例有 `/tmp`、`/mnt/user-data/outputs` 路径，不能直接照搬。
- 主说明要求先黑盒执行再读源码，与本项目先审查再执行的目标冲突。浏览器下载需网络，截图/日志可能含敏感信息；需要启动本地服务、浏览器、写文件权限，测试页面还可能发出外部请求。
- 安装前确认：允许的启动命令、浏览器/下载权限与输出目录，先审核脚本再执行，限制隔离本地测试页；本次未验证 Windows 运行。不能因安装技能就默认安装 Playwright 或浏览器。

### 5. find-skills — 待确认（发现工具不等于安全审查）

- 原始位置：`vercel-labs/skills` → `skills/find-skills/`；[固定版本 SKILL.md](https://github.com/vercel-labs/skills/blob/a80e4c9d12d607631249d4d7d059f835d4b2f13a/skills/find-skills/SKILL.md)。Vercel Labs 来源；[许可证](https://github.com/vercel-labs/skills/blob/a80e4c9d12d607631249d4d7d059f835d4b2f13a/LICENSE)为 MIT；维护快照见上表。
- 子目录只有 SKILL.md，没有脚本，但其工作流会调用 Skills CLI 搜索、安装和更新，并访问 skills.sh/GitHub/npm；只读 Markdown 本身不需要 CLI，实际搜索工作流会执行外部程序。
- 可辅助寻找候选，和项目框架无关；不能代替现有 skill-installer 或源码/许可证审查。说明中偏重安装量和星数，并给出全局、跳过确认的安装选项，与本项目逐项授权要求不一致。
- 安装前确认：仅用于发现、逐个人工/正式任务批准，不自动全局安装或更新；另审 CLI 版本、依赖、遥测/网络端点及写入范围（本次未审 CLI 实现）。本次未运行任何 npx 命令。

## 研究后未列入安装建议的方向

数据库迁移：已读 `wshobson/agents/plugins/framework-migration/skills/database-migration/SKILL.md`（[固定版本](https://github.com/wshobson/agents/blob/0874a27b17a22e2b7c2e2bcd725768e0803cad06/plugins/framework-migration/skills/database-migration/SKILL.md)）。主体是 Sequelize/TypeORM/Prisma，不是 SQLAlchemy 2/Alembic；有回滚、删除表与部署示例，不适合直接导入本项目。保留当前迁移协议与官方文档，后续若要本项目专用迁移技能，应另下发任务；本次不制作或安装。

Python/FastAPI 审查：检查了同仓库 `plugins/python-development/agents/fastapi-pro.md` 和 `plugins/api-scaffolding/skills/fastapi-templates/SKILL.md`。前者是带模型偏好的 agent 配置，不能当作标准 Skill 目录直接安装；后者偏新建 async 项目与认证模板，不等于当前同步 SQLAlchemy 服务的缺陷审查规则，还可能引入范围外技术。当前先使用已有代码审查流程及 pytest 建议，不为凑数推荐一个“FastAPI 专用”名称。

React/Next 专用候选不会因为流行就优先于 Vue：本项目没有 React/Next 运行时，重建为其他前端框架不属于 Skills 配置任务。

## 后续决策与验收

建议先审定两个纯说明候选 python-testing-patterns、frontend-design；Vue、Playwright 与 find-skills 分别确认默认规则、脚本/Windows 权限、CLI 安装边界。每项授权须明确仓库/子目录/固定提交、安装作用域、许可证保留、是否允许联网或脚本；任何第三方指令不能覆盖正式任务和 AGENTS.md。

本次验证仅为文档/source 核验及 `git diff --check`、暂存清单检查。不会为文档调查运行业务测试、第三方脚本或前端构建。切回 main 基线后，先前开发留下的 frontend/node_modules 为未跟踪本地产物（main 尚无该忽略项）；只显式暂存本评估文档，不清理或提交这些产物。最终 PR 应仅有此文件，base=main；不自动合并或部署。
