# 个人 Telegram 通知（TASK-0051）

本版取代 TASK-0050 的平台共享设置。所有已登录且启用的账户均可访问侧栏“消息设置”与 `/notifications`；owner/admin 只能设置自己的 Telegram，不能读写或代发给其他账户。Telegram 是唯一渠道。旧 `/api/admin/notifications/telegram` 已移除，`notifications.manage` 管理权限已废弃；旧服务滚动切换期间，前端仅识别该旧权限名，不赋予它任何功能。

## 身份验证与自助绑定

1. 平台维护人员配置统一机器人；用户无需创建自己的 Bot，页面不接收 Token 或任意 Chat ID。
2. 当前登录用户通过 Origin/CSRF 保护的 `POST /api/me/notifications/connect` 创建 256-bit 随机一次性配对链接。数据库仅保存 SHA-256 摘要、发起会话摘要、账户和五分钟到期时间；新链接覆盖旧链接。重新连接立即关闭并撤销原绑定，防止排队消息流向旧地址。
3. 浏览器暂存链接，用户在自己的 Telegram **私聊**点击 Start。固定回调路径接收 Telegram 消息，验证平台 webhook 密钥、HTTPS 与配置的 Host。只接受非 Bot 的真实 private chat，且 chat ID 与 sender ID 相同、为正整数且小于 2^52。群组、超级群、频道、转接账户和任意 URL 均不作为绑定目的地。
4. 回调在共享数据库互斥事务内核实一次性摘要、TTL、原登录会话仍有效及账户仍启用，消费摘要并暂存候选身份；此时**没有完成绑定，也不发送通知**。重复或无效回调统一返回 `ok=true`，不透露账户、令牌或地址是否存在。
5. 用户返回网页检查连接状态，并确认刚才由自己的 Telegram 完成操作。网页显示候选身份尾号，需当前发起会话再次通过 Origin/CSRF 确认。过期、已注销或更换登录会话无法确认。成功后保持通知关闭，用户选择偏好并保存启用。
6. Telegram 私聊 ID 全库唯一：一个 Telegram 身份只能绑定一个平台账户。冲突返回泛化 409，不透露占用者。断开连接删除挑战、清空私聊身份并更新版本；重新配对和断开均使旧排队版本失效。

链接是短时 bearer 凭证，不能分享、由他人代点或放进截图/日志/客服消息。不要仅凭看到候选状态就确认，必须是本人刚才操作。网页链接采用 `noopener noreferrer`、no-referrer，无自动复制、localStorage 或历史重放；原始配对链接仅在创建时返回，刷新后可重新生成。服务端响应均 no-store。界面和 API 仅显示身份末四位，不暴露完整 Telegram ID、会话摘要、挑战摘要或平台密钥。

## 配置、webhook 与部署前置条件

功能默认关闭，缺任一条件时 UI 显示平台未就绪、Connect/测试不可用：

- `RUNTU_TELEGRAM_BINDING_ENABLED=true`：维护人员确认下面条件后显式打开。
- `RUNTU_TELEGRAM_BOT_TOKEN`：统一 Bot 的服务端环境密钥，SecretStr 持有，不写入数据库/API/UI/日志。
- `RUNTU_TELEGRAM_BOT_USERNAME`：与该 Token 对应的真实 Bot 用户名，不含 @，仅用于生成固定 `https://t.me/<bot>?start=...` 链接。维护人员须通过官方 Bot 管理核对，错误配置只会导致配对无法完成，不可绕过回调证明。
- `RUNTU_TELEGRAM_WEBHOOK_SECRET`：独立高熵随机 32–256 位 URL-safe secret，不能复用 Bot Token，不能放进 URL；服务端恒定时间校验 `X-Telegram-Bot-Api-Secret-Token`。
- 已审查并另行授权的 `0008_notifications` 和 `0009_account_notifications` 升级，及运行新代码的后端。
- 配置的 HTTPS `auth_origin` 可接收 Telegram 回调，公开证书有效。代理须明确限制信任来源，并保留真实 HTTPS scheme 和配置 Host；不能信任任意转发头伪造 scheme/host。

**本任务没有执行这些部署动作。** 维护人员另行授权后，用保密的服务端程序向固定 `api.telegram.org` 的 `setWebhook` 注册 `https://<配置的认证主机>/api/telegram/webhook`，设置上述 `secret_token`、`allowed_updates=["message"]`，切换时明确决定丢弃旧 update（推荐 `drop_pending_updates=true`）。不得把含 Bot Token 的请求 URL 贴入 shell 历史、访问日志或报告。确认 Telegram 已接受 webhook 后再开放 feature flag。

本版使用 webhook，不启动 `getUpdates` polling；同一个 Bot 不应同时交给其他轮询器、webhook 或多个平台消费。回调密钥、请求体和响应体禁止日志采集，错误回执只给固定摘要。未提供可从浏览器设置 webhook 的入口。轮换密钥须协调 Telegram 和平台，旧密钥不再接受；已有一次性挑战应断开/重新配对。关闭 feature flag 可停止新绑定和队列发送，用户仍可撤销本人的连接。

## 数据迁移与隐私

0009 新增三张表：每账户偏好与已验证私聊、短时挑战、按事件/收件人联合主键记录的投递占位。默认没有账户绑定，也不会从共享 Chat ID 推断身份。旧 0008 singleton 保留隔离，但迁移关闭其 enabled/registration 并推进版本；旧地址不进入新个人 API，也不会被路由使用。回退旧代码不会自动恢复旧共享订阅。保留的旧地址需由维护人员在授权流程中明确清除或归档，不能默默赋给任何账户。

绑定、解绑、偏好保存与审计同事务，审计只记录动作和本人账户，不包含 Telegram ID、挑战或密钥。发送前的投递占位单独提交，网络失败不回滚注册或账户操作。解绑/取消所有挑战后才能 downgrade 至 0008；进一步 downgrade 仍要求先清理旧全局配置，并保留注册待审核保护。迁移仅在一次性 SQLite/PostgreSQL 测试库运行，本地真实库未变。

挑战到期后不可再使用，即使记录尚未清理；用户断开或新建配对会删除/替换旧记录。投递占位可在事件五分钟时效之后由另行授权的保留策略清理，但不能重放历史事件。删除账户前须清理相关外键记录；若账户已不存在、停用、会话撤销或角色改变，发送和绑定均关闭保护。没有新增账户删除功能。

## 事件路由

| 事件 | 当前来源与收件人 |
| --- | --- |
| 注册申请 | 仅新建、提交事务成功且需要审核的 `registration_submitted`。只向当前启用、已验证、主动开启个人通知与注册订阅、当前仍为 owner/admin 的账户发送。绑定/偏好在事件之后改变时不补发。无用户名、密码、IP 或申请详情。重复用户名、直接登录型注册和回滚不触发。 |
| 我的工具任务结果 | 暂不可用，固定关闭。没有真实统一任务结果事件源，不能把模块配置操作伪装成任务完成。未来接入必须使用执行人的账户并重新检查工具授权，禁止广播给其他用户；本版无此路由。 |
| 账户安全、系统错误 | 暂不可用，固定关闭。没有专用脱敏、聚合来源，不转发原始审计或异常。 |

每个收件人发送前重新核实当前账户、角色、已验证绑定、偏好和版本；事件/收件人占位在数据库互斥事务中去重，跨进程、重放和并发最多尝试一次。旧绑定版本、过期事件（五分钟）及已处理的申请不发送。网络发送不持有业务互斥锁；已在途请求不能撤回，解绑阻止后续排队消息。

## 队列、测试与失败策略

- 一个守护线程、最多 16 项内存队列，注册只做非阻塞入队。收件人按 20 条一页读取；每个收件人仍单独核实和去重。队列满、限流、退出、缺少配置或存储/网络失败会丢弃，不扫描历史、不自动重试，不承诺送达。
- 测试只发送给请求人的已验证私聊：每人每五分钟一次，平台每五分钟最多 20 次。全部发送另有限制：每人五分钟 5 条、平台 100 条。换会话不能绕过账户限流，换账户也受平台上限约束。
- 固定证书验证的 HTTPS Telegram API，2 秒 socket timeout，不跟随重定向或环境代理，不接收自定义目的 URL。标准库连接显式关闭 wire debugging，避免 Token 路径日志。响应最多 8192 字节，仅 `200 + ok=true + message_id` 才算成功，原始异常和上游描述不回显。
- 测试 API 最多等待 3 秒，超时返回未确认，不能当作成功或立即重试。极慢 DNS/网络仍可能占据唯一线程，但线程与队列有界，业务提交不等待 Telegram。
- 被屏蔽、权限错误或其他传输失败统一安全反馈，并暂停对应账户通知；用户检查机器人后可重新保存启用。失败不影响其他账户配置，迟到的旧绑定失败不能暂停新版本。测试成功只证明 Telegram 接受该次消息，不证明用户已阅读。

## 自助 API 与验证

`GET/PUT /api/me/notifications`；`POST .../connect|confirm|disconnect|test`。账户始终从已认证会话推导，不接收 target user、Chat ID 或 Bot Token；GET 拒绝额外 query，写入拒绝额外字段。POST 仅接收 `expected_revision`；PUT 接收 enabled、受支持事件和 expected_revision。匿名拒绝，普通用户与 owner/admin 一样只能管理本人。

测试覆盖 A/B 隔离、普通用户、特权订阅路由、候选不发送、一次性重放/过期、撤销会话、群组/频道/伪造 sender、确认并发、共享 Chat ID 冲突、角色改变、停用、解绑旧队列、每收件人并发去重、回滚、限流、暂停、截止时间、迁移转换及真实 TLS 主机边界模拟。PostgreSQL 的原 11 项必需用例复用同一已验证绑定→测试→解绑契约。全部发送是模拟传输；没有真实 Token、Telegram 请求、数据库升级或服务重启。

[个人消息 UI 截图](ui/TASK-0051/README.md)。旧 TASK-0050 截图是历史迭代，不能作为当前共享配置语义。官方依据：[Deep linking](https://core.telegram.org/bots/features#deep-linking)、[setWebhook](https://core.telegram.org/bots/api#setwebhook)、[sendMessage](https://core.telegram.org/bots/api#sendmessage)。
