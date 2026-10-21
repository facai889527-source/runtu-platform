# TASK-0013 · 堆叠集成审查与安全合并方案

## 结论与边界

本报告基于实际抓取的 main 和 PR head，不执行合并。完整产品候选树没有文件冲突，本地 Python/Node/构建通过；默认应用没有管理写 API。**这些证据不等于已获合并授权、GitHub CI 已验证产品或具备生产安全能力。** 下一阶段认证/权限/审计只在本报告中规划。

正式 main：`b659c22fa8af3be42f107ec8149240b6f77e3efb`（首次及审查中再次 fetch 一致）。审查分支 `codex/TASK-0013-integration-review`，base=main；本 PR 只新增本报告和 `.github/workflows/ci.yml`，不复制产品代码。幂等键 TASK-0013:13，自动触发 2026-10-21T03:46:06.525Z，领取前本地无执行记录、全部状态搜索无同任务 PR。

## PR 链与实际范围

原始 `GET /repos/facai889527-source/runtu-platform/pulls/<n>` 快照：下表全部 **open、merged=false、各1个提交**。未发现被关闭或合并的条目。base/head 为 API 报告值，merge-tree 使用 fetch 后真实远程 refs。

| PR | base / API base SHA | head SHA | 相对父提交的实际增量 |
| --- | --- | --- | --- |
| #3 | main / `d4e379ca25b6f977deb380e92e2c62e41576f24b` | `4c1d1a41e302fde32ed36e0cc11fa8fdc0b98ffa` | 19文件：FastAPI工厂、设置/模块注册、只读健康和模块清单、Vue/Vite、依赖/锁文件、4项初始测试、开发文档 |
| #4 | codex/TASK-0003-platform-bootstrap / `4c1d1a41e302fde32ed36e0cc11fa8fdc0b98ffa` | `78ed8591ee12c045524c6120694396ebbbb774a1` | 6文件：模块生命周期/公开配置模型、只读详情、禁用路由隔离及测试/展示 |
| #5 | codex/TASK-0004-module-core / `78ed8591ee12c045524c6120694396ebbbb774a1` | `641e1428fd400c7b75a79009714cfab07a3f7704` | 17文件：SQLAlchemy/Alembic、数据库就绪、内部配置服务与迁移/测试/说明 |
| #9 | codex/TASK-0005-persistence / `641e1428fd400c7b75a79009714cfab07a3f7704` | `196d20ebd8067bbba79d1c00f2b288c28e69f58e` | 19文件：中文只读后台、请求管理、搜索/筛选/详情、测试和真实截图 |
| #10 | codex/TASK-0009-admin-ui / `196d20ebd8067bbba79d1c00f2b288c28e69f58e` | `52cd46e5c6405afec34dfbd5658f1db26f23c12f` | 15文件：History路由、真实链接、404、焦点/抽屉与回归测试、文档/截图 |
| #11 | codex/TASK-0010-routing-polish / `52cd46e5c6405afec34dfbd5658f1db26f23c12f` | `8435718acc731eaeccd1f9d649ddfbbb9e90e9d4` | 21文件：视觉系统v2、本地SVG、排版/信息区块、对比度测试及截图 |
| #12 | codex/TASK-0011-premium-ui / `8435718acc731eaeccd1f9d649ddfbbb9e90e9d4` | `ca77d7b7a4fdc882e9e3de9b40fde80f222c7249` | 14文件：可读性、自适应目录、手机顶栏、夹具回归、真实/夹具截图与路线图 |

对应产品链：`#3 → #4 → #5 → #9 → #10 → #11 → #12`。每次实际范围由 `git diff --name-only <parent>...<head>` 核对，与 API changed_files 一致。

独立文档 PR（各1文件，不是产品堆叠依赖）：

| PR | API base SHA（base均main） | head SHA | 唯一增量 |
| --- | --- | --- | --- |
| #6 | `8ea539836830aacc329714da642d22ebcc6a0780` | `0bc79a112d15bf29a89066828814cce7b825a1dd` | docs/CODEX_SKILLS_REVIEW.md |
| #7 | `2e5976f133d1414d99f13c15969a9862523b0322` | `38fb5b27b2882b716ab937a5ecfa5b5e234245b7` | docs/CODEX_SKILLS_INSTALL.md |
| #8 | `e9b7db1337cd9a45ecebb7f8ad2c025009d55dd7` | `77e30be3bc97cbacf74aca94b1468864340c743f` | docs/INTEGRATION_PREFLIGHT.md |

#7记录当时受权限约束的安装阻塞；后续交互会话经用户授权已完成四个Skills安装/识别，不能用历史报告断言当前仍未安装。#6/#7/#8建议作为带日期的历史记录单独审阅，本任务不修改它们。

### GitHub 状态的不确定性

#4/#5/#9/#10/#11/#12 原始 API 为 `mergeable=true, mergeable_state=clean`；#3/#6/#7/#8 初次快照为 `null/unknown`。随后再次GET #3，已变为 `mergeable=true/clean`，仍open未合并；初次unknown没有被误报冲突。#3 的 API base SHA 与实时 main 不同，本审查没有拿旧 base 替代最新 main。null 代表 GitHub 尚未给出合并计算结论，**不是冲突证据**，也不能说“GitHub确认可合并”。[GitHub REST 说明](https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request)。合并前须重新读取状态、审查与检查结果。

## 合并兼容性证据

仅执行 `git merge-tree --write-tree <left> <right>`，退出码均0，无冲突文件。该命令写入本地对象，不移动/提交/推送任何原分支。

| 检查对象 | 输出 tree SHA |
| --- | --- |
| 最新main + 最终#12 | `d7c39b1542fb937b32161ddbbffaeb2108597a08` |
| #3 + #4 | `0007cb510c2215f2d80bbb8be44e6ff79d6858e5` |
| #4 + #5 | `60b2af4ec09cbeeb4b2b9bcaa16f08dd4385919a` |
| #5 + #9 | `dd714c9054ccc35e975ca27918d5a7b3b53b9c05` |
| #9 + #10 | `a69f54e3feeba6b94941e74490cd70123d87ce47` |
| #10 + #11 | `b49007132ba7f17a923d4973ad53e3f82375e699` |
| #11 + #12 | `3cb44e16c3b23dc25c8ab0d892fb443120b7a0c7` |
| 最新main + #6 | `56a3fb7d1d16c31f482d6be3b06f7b8a56d15291` |
| 最新main + #7 | `d6fa6f884824ade42bc9dfefc02bf98540748ec5` |
| 最新main + #8 | `a544ccfca34c87f2686bf53425ba3b4f8332fdc5` |

相邻父子检查与最终main兼容检查是不同证据：父子包含关系本身不能取代最新main集成测试。main若有新提交，必须重新计算最终候选树及受影响验证，本表不能永久复用。

## 完整候选树验证与安全核查

使用 `git archive` 导出上述最终 tree，未在当前 main 派生分支复制产品代码。命令与真实结果：

| 验证 | 结果与范围 |
| --- | --- |
| root .venv Python 3.14.0，在候选根执行 `python -m pytest tests -q` | 22 passed；既有 Starlette/httpx 弃用警告1条 |
| 候选 frontend，pnpm11.25.0 `install --frozen-lockfile --offline` | 锁定安装通过，35包来自缓存，downloaded=0，无依赖/锁文件变化 |
| Node24.19.0 `node --test tests/ui.test.js tests/navigation.test.js tests/design.test.js` | 8 passed，涵盖原搜索/请求、History解析与安全路径、核心色对比度 |
| 候选 frontend `pnpm run build` | Vite构建通过；index引用的 `index-DTX_Jzi8.js`、`index-DpKDUJ0T.css` 均真实存在 |
| `git diff --check origin/main origin/codex/TASK-0012-ui-refinement` | 通过；本审查暂存区另做diff检查 |
| `python -m pip check` | No broken requirements found |
| 实际候选应用 OpenAPI | 业务API路径只有 `/api/health`、`/api/modules`、`/api/modules/{module_id}`，均仅GET；默认demo没有附加业务路由 |
| 实际 Vite `/api/health` 代理 | 返回status=ok、database=not_configured，与后端一致 |
| Chrome + 完整隔离候选树浏览器脚本 | 1440/1280/390/360、直接访问/刷新/前进后退、筛选保留、键盘/抽屉、无水平滚动/JS异常，以及明确0/1/3/8夹具、降级/失败/重试回归 |

最初将候选放在 `.git/codex-coordination/review13/candidate`，Python/Node/构建在该树通过，但Vite按默认安全边界拒绝服务.git中的源文件；随后将**同一tree ZIP**导出到工作区兄弟目录 `.runtu-review-0013` 做浏览器验证，没有修改Vite或放宽安全设置。浏览器结果在该快照的 `.git/codex-coordination/ui12/`。纯 main 同样干净导出为 `.runtu-review-main-0013` 验证 CI 门禁；没有因原开发目录残留测试缓存而把它误判成产品。

### 文件/敏感信息核查

最终 tree 共88个跟踪文件，按路径核对：没有 `.env`、IDE、.venv、node_modules、dist、数据库文件/备份或浏览器缓存。只读文本模式扫描私钥头、常见Token特征、带凭据URL及远程shell管道，未发现私钥/Token或curl/wget管道；带凭据URL仅命中 `.env.example:4` 和开发文档中的 `USER:PASSWORD`占位样例，不是真实凭据。没有读取本地真实.env、系统密钥库或GitHub secrets。正则扫描不等于完整泄露检测或依赖安全审计。

#12的7张PNG签名/尺寸有效，真实图与fixture图已分开标识；桌面1425px图片宽度源于1440px视口扣除滚动条，full-page高度可超视口。五张真实图来自默认demo，未配置数据库；两张fixture图不代表已接入真实业务模块。可审阅[固定#12提交的截图目录](https://github.com/facai889527-source/runtu-platform/tree/ca77d7b7a4fdc882e9e3de9b40fde80f222c7249/docs/images/task-0012)。

### API、配置、数据库与前端边界

- app.py核心只有GET；ModuleConfigService.save是Python内部接口，没有HTTP保存/删除/启停入口。不能据此推断任意第三方模块都是只读：模块可提供自己的router，未来必须另行做路由/权限审查，不能在未认证时开放写能力。
- 公开配置是严格的bool/int白名单，未知字段拒绝；持久化只投影两列，禁用状态保留配置；HTTP存储失败返回通用503，不回传底层异常或URL。manifest的名称/描述仍是开发者提供的公开数据，须人工避免写入机密，白名单不能保证任意文本含义无敏感性。
- 数据库URL来自.env/环境并用SecretStr，支持明确驱动；连接惰性建立、超时、会话/事务回滚；启动不自动迁移，不调用create_all。首次/重复升级、降级、白名单/唯一约束与回滚通过SQLite测试。尚无真实PostgreSQL在线证据，不能把离线SQL/SQLite当成PG通过。
- frontend使用固定同源API前缀，模块ID验证/编码/解码，拒绝外站与反斜杠导航，不使用v-html渲染服务端文本；请求超时/取消/generation隔离迟到结果。列表格式只有基础校验，未来外部模块契约可进一步验证，当前默认后端受Pydantic模型约束。
- Vite仅本地host与既有API代理；History路由静态部署仍需fallback，API/静态资源不能错误返回HTML。Nginx示例仅文档，未部署。应用无认证、授权、审计、CSRF或速率限制；本地只读验收不授权公网暴露。

## CI 评估与本 PR 的变更

main跟踪树没有 `.github/workflows/`；Actions runs API初始返回total_count=0，#12 combined status为pending但statuses=[]/total_count=0，不能说CI已通过。main分支API为protected=false，可见rulesets=[]，没有配置保护规则；本任务不修改保护。连接器拒绝了workflows集合端点（允许列表限制），因此工作流存在性以git跟踪树和runs证据交叉核对，未尝试访问secrets或提高仓库权限。

新增 `.github/workflows/ci.yml`：

- 仅pull_request及push main，`contents: read`，使用GitHub托管ubuntu-24.04；没有secrets引用、写权限、部署、pull_request_target、self-hosted或checkout后凭据持久化。
- 三个官方action按真实GET refs与固定提交action.yml核验，均node24运行时：checkout=`d23441a48e516b6c34aea4fa41551a30e30af803`；setup-python=`ece7cb06caefa5fff74198d8649806c4678c61a1`；setup-node=`249970729cb0ef3589644e2896645e5dc5ba9c38`。可变v6标签只用于此次核验，工作流使用完整SHA。
- 先检查backend/frontend哨兵文件。纯main没有产品时输出明确skip summary；不把跳过当产品通过。产品存在但缺少必需文件则失败；有产品时运行Python3.14、pip check、Node24、固定pnpm11.25.0、frozen安装、所有*.test.js与build；早期无Node测试文件时明确说明，构建仍必须执行。
- 不启用依赖缓存，降低跨PR缓存污染；setup-node关闭自动包管理器缓存。pnpm依据现有锁文件及仅esbuild允许脚本的workspace规则，未改变原依赖策略；只安装包管理器本身时ignore-scripts。Python依赖仍是范围约束，没有锁定哈希，不能宣称完全可复现；Python/Node次版本允许补丁更新，后续需单独审查依赖锁定与更新机制。
- 本地已从YAML抽取实际Bash门禁：干净main输出backend=false/frontend=false及两条skip summary；完整候选输出true/true；只有app.py但缺少必需文件的隔离夹具被正确拒绝。静态检查确认action完整SHA、只读权限、无secrets/特权触发器和persist-credentials=false。没有安装额外YAML解析器，不将静态检查称为GitHub runner执行。

安全取舍依据[GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)。**本PR基于纯main，所以其CI即使成功也只证明门禁，产品测试会跳过。** 此workflow合入且相关产品PR更新/重定base后，才会对含产品的PR合并引用运行。不得把本地Windows测试当作Linux Actions成功，不能把未出现的runner结果虚报绿色。

## Blocker 与非 blocker

| 分类 | 项目 | 处理 |
| --- | --- | --- |
| 合并前 blocker | 尚无本任务之外的明确合并/重定base授权；各项实时审查/检查仍须确认 | 等待用户授权、审查通过、实时状态明确；本次不执行任何合并操作 |
| 验证 blocker | 含产品的GitHub Linux CI未实际执行；当前纯main CI会跳过产品 | CI先审查，再在授权整合流程中要求含产品的检查真正运行；不能把skip当pass |
| 生产/PG验收 blocker | PostgreSQL在线迁移、约束/时区/并发和恢复未实测 | 按下方步骤在隔离实例补齐；不阻止当前SQLite/只读本地原型审查，但阻止PG生产就绪宣称 |
| 生产/写能力 blocker | 无认证/权限/审计/CSRF/速率限制 | 仅计划TASK-0014，未受保护写入口禁止开放，不授权生产部署 |
| 非 blocker | Python范围依赖未hash锁定、既有Starlette/httpx警告 | 后续正式维护任务；本次不擅自更新依赖 |
| 非 blocker | 完整读屏/跨浏览器、像素差分和大规模性能未验证 | 现有四尺寸/八模块夹具只是有限证据，后续扩充 |
| 非 blocker | #7安装报告反映旧阻塞 | 单独审阅历史文档，避免被误当现状；不更改原PR |

## PostgreSQL 在线验证缺口与明确步骤（待单独环境授权）

1. 提供可丢弃的隔离PostgreSQL实例，明确版本、数据库/角色与最小DDL/DML权限，使用正常安全配置渠道传入RUNTU_DATABASE_URL；不把真实连接串写入本报告、源码或命令日志。禁止借用生产数据库做测试。
2. 从空库运行 `python -m alembic upgrade head`、`python -m alembic current`，检查0001、表/列/唯一键/check约束；重复升级应不重复建表。启动应用后/api/health须database=ready，详情读取真实默认/保存后的白名单配置。
3. 在专用PG集成测试中使用真实连接验证内部save/load/update/create_only重复冲突、异常事务回滚、重建连接后持久化、禁用保留/未知模块拒绝；不能仅给现有SQLite测试设置环境变量就声称已改测PG。
4. 补充UTC带时区往返、字符串长度与check约束、并发插入/更新、最小权限、连接中断/超时；配置不可用或未迁移时health/详情应503且不泄露凭据。
5. 在可丢弃副本执行downgrade base/再upgrade、备份恢复和失败迁移回滚演练。downgrade会删除表，不能自动在生产执行。Git代码回退不等于数据库数据恢复。
6. 保存脱敏的版本/命令/断言证据，环境失败时明确阻塞。上述步骤本任务未执行，没有安装/启动数据库或使用真实凭据。

## 合并策略与用户授权清单（只建议，未执行）

推荐**普通merge commit**：保留每个产品父提交的祖先关系，使下一层PR重定base后仍只显示自己的增量。当前链每PR一个提交，squash/rebase不会带来足以抵消重放风险的收益。若用户选择squash/rebase，必须另行授权以原父SHA为边界重放子增量并重新验证；不能简单强推或复制整个链。

授权后的建议流程：

1. 先审阅本PR文档/CI，决定是否合入基础CI；任何main变化后fetch并重算最新main+#12候选。#6/#7/#8独立文档可单独排期，不是产品链的前置依赖。
2. 重新确认所有head SHA、状态、审查、检查结论。#3 unknown或检查失败时停止，不根据本地无冲突强行合并。含产品的CI必须真跑，skip不能满足该门槛。
3. 得到具体授权后普通merge #3，fetch确认 `git merge-base --is-ancestor 4c1d1a41e302fde32ed36e0cc11fa8fdc0b98ffa origin/main` 成功。
4. 仅在授权下将#4 base改为main；检查 `git diff --stat origin/main...origin/codex/TASK-0004-module-core` 和 `git log origin/main..origin/codex/TASK-0004-module-core`：应只有本任务6文件/一个增量提交，无#3重复代码；重跑相应检查后普通merge。
5. 依次对#5、#9、#10、#11、#12重复“确认前父head已是main祖先 → 重定base main → 检查三点diff/提交 → 测试/CI/审查 → 普通merge”。各增量文件数参考17/19/15/21/14；main如有独立同文件改动，重新审查而非机械以数量作唯一标准。
6. 每步记录新的main SHA、合并commit、实际CI链接及审查结果；main变化或父分支异常时停止重算，不继续使用旧merge-tree表。不自动删除或关闭任何PR/分支。

需要用户另行明确授权的操作包括：合入本CI/文档PR、逐个合并产品PR、逐个修改子PR base、是否合入独立历史文档、配置分支保护/required checks、申请PG隔离环境与在线演练、任何生产部署。**本任务没有执行merge、rebase、force-push、base修改、关闭PR或部署。**

### 失败与回退

发生测试、CI或diff异常，保留当前分支/状态证据，停止后续合并并另发修复任务。若已合入代码需要回退，使用新的审查PR执行 `git revert -m 1 <merge_commit>`；有后续依赖时先分析并按依赖逆序回退，不能reset/force-push main。迁移/数据的备份恢复独立授权，不因revert代码就自动downgrade。回退后重跑检查并记录残留风险。

## TASK-0014 安全设计草案（仅规划）

建议先定义受保护的同源浏览器后台身份模型和权限矩阵，再编码。以下是设计候选与验收边界，不是已实现功能或现成生产方案。

| 领域 | 建议设计与必须验证的负例 |
| --- | --- |
| 会话/Cookie | 服务端可撤销的随机不透明会话，库中只存必要验证值；登录/提权轮换、防固定会话、闲置/绝对到期、退出/禁用撤销。生产HTTPS，Cookie显式Secure、HttpOnly、SameSite，优先评估__Host-与Path=/、不设Domain；跨站进入体验和开发HTTP另行明确，不能把关闭Secure当生产方案 |
| CSRF | 受保护的状态变化使用会话绑定CSRF令牌并验证来源，拒绝缺失/错误令牌；登录/退出也评估CSRF。SameSite是纵深层，不替代CSRF设计；GET不改变状态，禁止泛化带凭据跨域 |
| 密码 | 采用成熟Argon2id实现与随机salt，不自制加密/明文/快速哈希；参数至少评估OWASP当前19MiB、t=2、p=1下限并按目标硬件/负载实测，支持升级重哈希。密码不入日志、审计或前端持久存储 |
| 首次管理员 | 由明确的本地/运维一次性引导流程创建，无默认账户/密码，无公开bootstrap写接口；原子“仅首次”与并发重放测试，消费后关闭引导能力；不把凭据放命令参数/源码 |
| 角色与默认拒绝 | 服务端统一依赖/授权策略，候选viewer/operator/admin须逐路由定义，模块操作/资源范围另验证；UI隐藏不是授权。未登录401、无权403及直接访问/跨角色负例；未声明权限默认拒绝，不让模块自行绕过核心 |
| 审计 | 登录成功/失败、退出/撤销、权限与管理变更记录操作者、目标、结果、关联ID与UTC；敏感字段不记，授权读取与保留/完整性策略明确；事务失败与审计写失败行为需定义 |
| 速率限制 | 登录/引导/敏感请求按身份和来源约束，明确代理信任链、重试/恢复与并发语义；防账号枚举和粗暴锁定拒绝服务；多进程一致性与测试要求先设计，不假设单进程内存足够 |
| 迁移/验证 | 用户、角色、会话、审计schema另立Alembic版本；空库升级、旧数据升级、唯一约束、并发引导、会话过期/撤销、审计脱敏与PG在线测试；破坏性降级需独立策略，不自动删用户/审计 |

上述会话、CSRF和密码建议分别依据[OWASP Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)、[OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)、[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)；首次管理员、角色/审计模型为本项目待审设计推断，需产品与威胁模型确认。先实现并验收认证/授权/审计，再另行发布管理写API任务，禁止先开放未认证写入口。
