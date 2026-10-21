# TASK-0007：两项 Codex Skills 安装预检与阻塞记录

日期：2026-10-21（Asia/Shanghai）；原生 heartbeat 触发时间：10:12:04.918+08:00。幂等键：`TASK-0007:7`。

**结果：两项均未安装。** 已完成只读来源与安装器预检，因目标目录不在当前沙箱可写范围内而停止，未执行安装器、未尝试越界写入，也未取得安装后的加载证据。不能将此结果描述为安装成功或“重启后即可使用”。

## 正式范围与基线

只接受 TASK-0007 指定的两个固定提交、固定子目录，不降级为 main，不安装其他技能。从远程 main `2e5976f133d1414d99f13c15969a9862523b0322` 建立 `codex/TASK-0007-skills-install`，PR base=main；不继承产品堆叠分支。领取前 GitHub 全状态查询无 TASK-0007 PR，本地无同版本记录。

本任务明确要求“如果安装失败或权限不足，也应在文档中如实说明，并提交仅报告结果的 PR”；同时要求遇到提权或范围外网络权限时停止。本次按此交付分支处理，不自行改变安装方法或安全设置。依据为[正式任务](../.coordination/tasks/TASK-0007.md)，不是第三方技能的建议。

## 固定来源复核

通过 GitHub 连接器的只读 GET，再次读取固定提交文件树、主说明、相关 references 与许可证。树查询没有截断；以下文件均为普通文件（100644），所选目录未发现独立脚本、可执行文件或符号链接。Markdown 内的示例代码不等于已执行代码。

| 技能 | 固定来源 | 核验到的文件 | 磁盘安装 / 会话加载 |
| --- | --- | --- | --- |
| frontend-design | `anthropics/skills` @ `dbd4588f9e1033efb41dad4bef2f7947c8993d44`，`skills/frontend-design` | SKILL.md、LICENSE.txt（Apache-2.0） | 未安装 / 未验证 |
| python-testing-patterns | `wshobson/agents` @ `0874a27b17a22e2b7c2e2bcd725768e0803cad06`，`plugins/python-development/skills/python-testing-patterns` | SKILL.md、references/details.md、references/advanced-patterns.md；另读仓库根 LICENSE（MIT） | 未安装 / 未验证 |

固定来源：[frontend-design](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design)、[python-testing-patterns](https://github.com/wshobson/agents/tree/0874a27b17a22e2b7c2e2bcd725768e0803cad06/plugins/python-development/skills/python-testing-patterns)、[根 MIT 许可证](https://github.com/wshobson/agents/blob/0874a27b17a22e2b7c2e2bcd725768e0803cad06/LICENSE)。本次未将源文件或用户目录内容放入仓库。

GitHub blob SHA 可供后续复核（不是本地安装文件哈希）：

| 来源文件 | Blob SHA |
| --- | --- |
| frontend-design/SKILL.md | `a5333457c414d20d625f307df945842c0952ecc3` |
| frontend-design/LICENSE.txt | `f433b1a53f5b830a205fd2df78e2b34974656c7b` |
| python-testing-patterns/SKILL.md | `4fe8a4245c55e9e79e70b5f75ab387e2349f91dc` |
| python-testing-patterns/references/details.md | `9b1647467d5fb7401ac3a6b109c9b75c1512bf6d` |
| python-testing-patterns/references/advanced-patterns.md | `da186a91e60c44339a28ddb3b6ce478b7d23af64` |

## 内置安装器的只读审查

使用的是当前用户 Codex 自带的 `.codex/skills/.system/skill-installer`，没有下载替代安装器。已阅读其 SKILL.md、`scripts/install-skill-from-github.py` 和 `scripts/github_utils.py`，未运行 `--help` 或安装操作。

源码支持 `--repo`、`--path`、完整 SHA 的 `--ref`、`--dest`、`--method download`。download 模式使用 Python 标准库经 `codeload.github.com/<owner>/<repo>/zip/<ref>` 下载固定版本，先写系统临时目录的 codex 子目录，再校验并复制选定技能目录；不会运行下载技能里的代码。下载阶段实际取得整份归档，最终只复制指定子目录。`auto` 可能回退 Git/SSH，因此若后续获批，优先明确 download，失败则停止，不变更固定版本。

默认目标是 `$CODEX_HOME/skills`，环境变量未设时为 `%USERPROFILE%\.codex\skills`。本机本轮 CODEX_HOME 未设置；两个准确的逻辑目标分别是：

- `%USERPROFILE%\.codex\skills\frontend-design`
- `%USERPROFILE%\.codex\skills\python-testing-patterns`

只读 Test-Path 对两个目标均返回 False；没有同名目录被覆盖。安装器也会拒绝已存在的目标，并对目录穿越/不支持的链接作校验。未用 --dest 把技能改装到项目目录来绕开边界。

只读核验本机安装器文件 SHA-256：

- install-skill-from-github.py：`110CC7E4E395C2C9BA070D47DB7D21BE5164591C35015AE364FC9C9905B08DE8`
- github_utils.py：`2F9702AFB9F0DA740181FA4A3214F663E460F80CD5CEA2E7DCAAB00AD269082E`

下载帮助代码可能使用进程已有 GitHub Token；本次仅阅读源码，没有读取、输出或修改任何 Token。网络安装端点是否在无人值守安装权限内未实际验证。

## 阻塞与未执行的调用参数

**主要阻塞：文件系统权限。** 当前沙箱仅允许工作区、指定可视化目录和临时目录等写入；用户 Codex Skills 目录只有读取权限。安装器最终必须向上述两个用户目标写文件，因此现有权限不足。安装器本身没有显示要求 Windows 管理员权限；这里是平台沙箱写入边界，不应混同为 UAC 管理员安装失败。未实际尝试写入、未收到工具运行失败或审批拒绝，不编造错误日志。

在此环境完成安装需要额外授权该目录写入，超出当前可写边界；按照正式任务的停止/报告条件，没有发起越界安装、关闭沙箱、修改 PATH/环境变量，或使用另一工具复制文件。

**另需确认许可证保留。** Python 技能的固定子目录不包含 LICENSE；MIT 许可证在仓库根目录。当前内置安装器只复制选中的技能目录，没有附带根许可证的参数。不能把只下载整仓归档但随后删除临时目录视为保留了版权/许可通知。本次没有自行添加第三方文件或扩大安装子目录；后续需明确一种符合许可证义务且受支持的处理办法，否则该项继续阻塞。

以下仅为审定后的参数记录，**没有执行**（省略 Python 与安装器路径，不是执行日志）：

```text
--repo anthropics/skills --ref dbd4588f9e1033efb41dad4bef2f7947c8993d44 --path skills/frontend-design --method download
--repo wshobson/agents --ref 0874a27b17a22e2b7c2e2bcd725768e0803cad06 --path plugins/python-development/skills/python-testing-patterns --method download
```

没有改用 main、npx、其他安装器或手动复制方案；没有安装 find-skills、vue-best-practices、webapp-testing、npm/pip 依赖。

## 文本匹配、风险与加载边界

非执行型任务匹配：frontend-design 的描述适合正式 UI 视觉/信息层级任务；python-testing-patterns 适合 pytest、隔离和失败路径设计。其参考资料含 requests、pip、CI 上传及旧 SQLAlchemy/测试示例，只有未来正式任务允许时才可采纳对应操作，不能因为安装技能就执行。没有测试这些示例，也不把示例中的占位文本当成真实凭据。

本次只能证明固定源可读、目录结构与预期一致、安装器参数支持固定版本。没有磁盘安装文件、没有安装后的发现/可调用证据；重启不能补足未安装状态。因此不报告“已加载”，也不以“需重启”掩盖权限阻塞。

后续若正式解决写入权限与许可证办法，应重新检查同名目录及固定内容，使用内置安装器，再只读核对磁盘文件与许可证，并在下一轮确认可用清单。若目录存在但未出现在清单，再依据实际版本记录是否需要重启。该后续操作不由本报告自动触发。

## 交付检查

仅新增本文件；`git diff --check`、暂存 diff 检查与文件清单核验。无需产品测试/前端构建，本次未运行。已有 frontend/node_modules 为之前开发留下的未跟踪产物，未改动、清理或提交。没有 Skills 文件、用户目录内容、凭据、数据库文件、IDE 配置进入提交。

不修改 AGENTS.md、产品依赖、#3/#4/#5/#6、自动化或三分钟 heartbeat；不提交 main、不自动合并或部署。当前任务交付为如实的阻塞报告，安装仍需后续解决上述前置条件。
