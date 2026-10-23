# Telegram 消息设置：公共 Bot 私聊里程碑（TASK-0053，部分交付）

TASK-0053 **尚未完整完成**。本阶段实现显式选择公共 Bot、私聊证明、主动选择私聊目标和 owner 跨账户管理；个人 Bot 绑定、群组发现/成员过滤及多目标投递仍未实现。界面明确禁用个人 Bot 入口，不接收 Token。TASK-0052 的认证加密/固定 API 基础保留，但没有个人 Token 持久化或轮换操作；不能把这些基础模块当成已交付的个人 Bot 功能。

## 账户与配置生命周期

新账户包括 owner，初始均无 Bot 选择、Telegram 身份、私聊目标、订阅和启用状态。配置了公共 Bot 不等于为账户自动选择它。点击“使用公共 Bot”才登记公共模式及服务端 Bot Token 指纹；重新选择先清除旧绑定、私聊目标、订阅、启用和配对挑战。指纹仅用于检测配置变化，不返回 API。

随后点击连接生成 256-bit 一次性 /start 链接：数据库只保存其 SHA-256 摘要、发起账户/会话、目标平台账户及五分钟期限。Telegram 只通过独立密钥认证、HTTPS/Host 校验的 webhook 提交候选。仅接受 private chat，非 Bot sender 的正整数 ID 必须等于 chat ID 且小于 2^52；群组/频道消息不能作为身份或目标。回调重新验证发起会话有效、目标账户启用、公共 Bot 选择匹配当前配置；跨账户时发起者仍须为 owner。消费挑战只保存候选，**不绑定、不发送**。

发起浏览器再次通过 Origin/CSRF 确认候选，才能建立身份。成功后私聊目标仍未选择，通知仍关闭。用户必须主动选择“已验证私聊”，再保存启用及支持的订阅；取消目标选择时页面同步关闭启用，保存增加 revision，使排队旧消息失效。当前每账户仅有一个私聊目标；一个 Telegram 身份仍只能绑定一个平台账户，冲突仅返回泛化 409。

断开清空 Bot 模式/指纹、身份/chat、目标、所有订阅、启用/暂停和挑战，返回原始未绑定状态。已发送或已经进入网络请求的消息不能撤回。重新连接同一 Bot 也会关闭通知、清除身份/私聊目标/订阅，并撤销旧挑战，必须重新确认和启用。公共 Token 配置变化后，旧绑定无法配对、确认或发送，需要显式重新选择并验证。

链接是短时 bearer 凭证，不存入 localStorage、日志、历史记录或截图，不可代点或仅凭候选状态盲目确认。界面仅显示候选/绑定末四位；外链使用 noopener noreferrer 和 no-referrer，响应 no-store。普通用户仅使用自己的 Telegram。owner 代管时，界面明确标注目标账户，目标 Telegram 身份需完成 Start，随后由发起管理会话确认；这是 owner 的显式管理权限，不是普通资料编辑权限。

## 权限与接口

所有启用账户可自助使用 `/api/me/notifications`。自助路径拒绝 target query、任意 Chat ID、user_id、Bot Token 等额外字段。owner 额外使用独立路径 `/api/admin/notifications/users/{target}`，可读取、选择公共 Bot、配对、确认、改偏好、测试或断开任意账户；admin/viewer 连指向自己的 owner 路径也不可使用。禁用目标可以被 owner 查看、关闭或断开，但不能选择、配对或启用投递。每次服务调用重新从数据库核实会话与角色；队列测试也检查当前 owner 权限和收件账户状态，owner 被降权后不能继续代发。

- GET 基础路径：读取已脱敏配置，无额外 query。
- PUT 基础路径：`enabled`、`private_target`、四个固定事件布尔值和 `expected_revision`。未知字段、未接入事件源、未验证目标均拒绝；viewer 不可订阅注册申请，即使 owner 代管也不能替其越权。
- POST `/choose-public`、`/connect`、`/confirm`、`/disconnect`、`/test`：只接收 expected_revision。
- POST `/api/telegram/webhook`：只允许下述独立回调认证，不使用浏览器会话替代 Telegram 证明。

owner 页面账户选择器使用现有 owner-only 用户列表，每页最多 20 条，并提供首批/下一批；切换目标会卸载旧表单、取消读取并清除一次性链接，不把一个账户的结果套入另一个账户。admin/viewer 页面不读取 owner 账户列表。普通资料权限未扩大。旧 `/api/admin/notifications/telegram` 保持移除。

## 操作员配置与迁移

功能默认关闭。操作员需独立审查并配置服务器端环境：

- `RUNTU_TELEGRAM_BINDING_ENABLED=true`。
- `RUNTU_TELEGRAM_BOT_TOKEN`：SecretStr 持有，仅环境配置，不写入 API/UI/日志。
- `RUNTU_TELEGRAM_BOT_USERNAME`：不含 @，需核对属于该 Token，生成固定 t.me 链接。
- `RUNTU_TELEGRAM_WEBHOOK_SECRET`：独立高熵 32–256 字符 URL-safe secret，不能复用 Token，不放 URL。回调恒定时间校验 X-Telegram-Bot-Api-Secret-Token。
- `RUNTU_AUTH_ORIGIN` 为正确外部 HTTPS origin，反向代理必须提供经过可信配置的 HTTPS scheme 和匹配 Host。不能伪造 origin 关闭认证。
- 由操作员通过 Telegram 官方管理设置固定 `/api/telegram/webhook`、独立 secret_token；本应用不自动注册、删除或接管 webhook。当前阶段仅处理私聊 message，群消息不做路由。

部署新代码前必须单独审查并授权 `0010_explicit_public_bot`（及前置 0008/0009）迁移。0010 **清空已有私聊绑定和挑战，禁用原订阅，revision 增加**；不把旧绑定转换为默认公共模式。该破坏性转换是为落实主动选择要求，需提前告知账户重新选择和配对。先做受控备份，禁止运行时自动迁移。

降级前需断开所有 Bot 选择/绑定/目标并取消挑战；跨多级回退还保留旧单例和待审核申请保护。检查失败不应先删除新增列。迁移与 downgrade、Alembic 元数据检查只使用临时数据库。当前真实库、后台进程和实际 Telegram 均未更改或验收；不能仅刷新前端就宣称已激活。

## 投递边界

只有真实注册提交事务成功后发出的 registration_submitted 事件会通知当前启用、已验证、主动选中私聊并 opt-in 的 owner/admin。撤销角色、停用账户、解绑、移除目标、修改版本或超过五分钟均抑制投递。账户安全/工具结果/系统错误未接权威事件源，保持不可用，无虚构工具通知。

继续使用单个 16 项 best-effort 队列、每事件/收件人持久化去重、固定 TLS Telegram sendMessage、无重定向/代理、2 秒 socket 超时、3 秒测试 API 截止及数据库限流。网络不持有业务互斥锁；未确认发送会安全暂停该账户，不重放历史事件。当前去重只适用于一个私聊；**多目标需要新的逐目标授权和去重设计，尚未交付**。

## 已验证与剩余范围

新增隔离测试覆盖 owner IDOR/RBAC、Origin/CSRF、发起 owner 降权、收件账户禁用、主动选择/目标移除/断开、配置轮换失效和迁移旧绑定重置；保留单次挑战、过期/重放、并发去重、审计回滚、限流/队列测试。Node 严格 DTO 和 owner 路径检查；全部拦截 API 的 Chrome 检查 1440/390/360、键盘目标选择、owner 管理不修改本人、admin/viewer 不读 owner 数据、私聊选择与失败暂停。

未完成：个人 Bot getMe/加密持久化/轮换/专属私聊证明，安全 webhook/getUpdates 冲突与独占/offset/lease，群组更新发现、当前成员/发送权限校验及 owner 全群组可见性，多目标选择/移除/逐目标去重与新 UI/完整集成验收。需正式后续任务继续，不自动启动下一任务。本阶段不能标记 TASK-0053 completed。

[当前里程碑截图](ui/TASK-0053/README.md)。[TASK-0052 安全基础](TELEGRAM_SECURITY_MILESTONE.md) 保留其历史边界；旧 TASK-0051 截图/说明不能代表当前主动选择行为。官方依据：[Deep linking](https://core.telegram.org/bots/features#deep-linking)、[setWebhook](https://core.telegram.org/bots/api#setwebhook)、[sendMessage](https://core.telegram.org/bots/api#sendmessage)。
