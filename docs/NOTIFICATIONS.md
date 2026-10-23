# Telegram 消息设置：个人与公共 Bot（TASK-0054）

本版交付可使用的个人 Bot 与公共 Bot 私聊流程、加密存储和 owner 代管；不是独立基础模块。页面以两种 Bot 为首要选择，owner 的“平台公共 Bot 管理”和“管理其他账户”默认收起，只有展开时才读取对应 owner 数据。未部署、未启用或未配置密钥时禁用不具备条件的选择，提供具体步骤，不把前端更新当成后端启用。

**明确剩余产品范围：群组发现、成员过滤、owner 全群组可见性、多目标选择与逐目标去重尚未交付。** TASK-0054 明确允许优先个人 Bot/UI；群组需正式后续任务，不能输入任意 Chat ID 或伪装群组已可用。只接入真实注册申请事件，其他事件源保持关闭。

## 账户操作

所有账户包括 owner 初始无 Bot 模式、身份/chat、目标、订阅或启用。任选一种：

- **公共 Bot**：平台配置就绪后点击“使用公共 Bot”。无需 Token，但仍须完成私聊证明和主动选择私聊目标。平台配置不是对账户的自动绑定。
- **个人 Bot**：在 Telegram 的 BotFather 创建仅供本平台使用的 Bot。点击“绑定个人 Bot”，输入 Token，并确认对其拥有控制权、专供本平台且未被其他部署使用。后端通过固定 HTTPS getMe 检查 is_bot、ID/Token 前缀和用户名；getWebhookInfo 必须明确没有 webhook，否则拒绝接管。验证和持有 Token 证明的是访问控制权，不声称能识别 BotFather 原始创建者。Token 提交后立即从输入清空，取消、错误或离开页面也会清空；不写浏览器存储，不回显 Token。

个人 Token 使用 TASK-0052 的 Fernet/MultiFernet，连同平台账户 ID 放入认证加密封套，数据库只存密文。解密校验账户、密文、指纹和当前模式；密文换账户、密钥缺失/错误、Token/配置变化一律停止对应路由。每个 Bot ID 只能由一个平台账户持有，公共 Bot ID 也不能作为个人 Bot 占用。API 只返回安全模式、Bot 用户名、就绪布尔值和末四位身份；不返回 Token、密文、指纹或更新 offset。

### 私聊证明与测试

1. 选择 Bot 后点击连接，产生 256-bit 一次性 /start 链接，五分钟有效；数据库只保存摘要、发起会话/账户、目标账户和期限。
2. 由预期的 Telegram 身份在该 Bot **私聊**中点击 Start。私聊 chat ID 与非 Bot sender ID 必须同为正整数且相等、小于 2^52；群消息不能作为证明。
3. 公共 Bot 由独立密钥认证的 HTTPS/Host webhook 接入，回到页面检查状态。个人 Bot 在页面点击“同步 Bot 消息”，经服务器持有的 Token 调用 getUpdates 读取；公共 webhook 不能消费个人 Bot 挑战。
4. 接入只消费一次摘要并产生候选，**不绑定、不发送**。发起浏览器核对末四位，再以原登录会话和 Origin/CSRF 确认。owner 代管时只有发起 owner 会话能确认，目标账户不能顶替。
5. 确认后通知仍关闭、目标仍未选择。主动选择已验证私聊，选择支持的订阅并保存启用，才可测试。每五分钟最多一次测试，返回成功仅在 Telegram transport 确认发送后；失败暂停，未确认不要立即重发。

重复、过期、撤销会话、目标停用、owner 降权或 Bot/版本变化均拒绝旧结果。链接不进浏览器持久化或日志；外链 noopener noreferrer/no-referrer、响应 no-store。不要公开分享或让无关身份操作。当前保持私聊 ID 全库唯一，即一个 Telegram 身份只能绑定一个平台账户；冲突不透露占用账户。

## 个人 Bot 更新与独占边界

不自动注册/删除 webhook、不自动接管其他部署，也不运行背景长轮询。个人更新仅由明确的同步操作触发，getUpdates 使用 timeout=0、limit=20、仅 message；每批最多 20 个更新、64 KiB 响应，已提交 offset 之前的消息不重复处理。配对消息深度在队列中时可继续同步，页面不会谎称已读完所有历史消息。

同步前核查没有 webhook；HTTP 409 或已有 webhook 安全失败。每账户数据库租约带唯一 ID 和 30 秒期限，网络不持业务锁；提交时重新核实发起者、目标状态、绑定版本、Bot 指纹、租约所有权和期限。失败不消费挑战或推进 offset，旧请求不能清除替代租约。角色撤销、失效结果和错误批次都会回滚。

**无法证明外部程序完全没有轮询。** 操作员必须先在原部署安全停止轮询/webhook，用户需明确承诺独占；本平台不会为了成功而自动 deleteWebhook。没有冲突响应不等于已证明独占，凭据外泄后也不能保证其他持有者不会再次使用。原部署必须由其维护者处理。Telegram 无法枚举全部历史群组，本版尚不提供群组发现。

## Owner、权限与清理

所有启用账户可使用自助 `/api/me/notifications`；admin/viewer 仅自助。owner 通过独立 `/api/admin/notifications/users/{target}` 和次要的账户选择器管理其他账户，包括个人 Token 替换、重新加密、私聊证明、偏好、测试或断开。API 每次从数据库重新认证，网络结果和队列测试也重新核实当前 owner 权限；不扩大普通资料编辑权限。禁用目标可被 owner 检查、关闭或断开，但不可绑定/启用发送。viewer 无注册提醒权限，即使 owner 代管也不越权。

切换公共/个人模式或替换 Token 前先完成外部验证，提交时清除旧身份、目标、订阅、启用/暂停、挑战及个人密文，必须重新配对。验证失败保留旧配置，界面不声称已切换。断开无需密钥也可删除所有个人密文和清空上述状态。重新配对关闭投递并清除旧身份/目标/订阅；旧 revision 排队消息被丢弃。已进入网络请求的消息无法撤回。

## 在服务器哪里、如何启用（需另行授权）

**本任务没有执行真实迁移、修改实际配置、重启或真实 Telegram 操作。** 页面可显示“需部署/启用”，并提供下述清单；不能仅刷新前端就声称可用。

1. 审查 PR27/PR28 的堆叠依赖、备份和迁移影响。部署包含 TASK-0054 后端/前端的版本。维护人员获得授权后，在项目根目录执行 `python -m alembic upgrade head` 并检查 `python -m alembic current` 应为 `0011_personal_telegram_bot`。0010 会清空旧私聊绑定并关闭订阅，需提前通知重新配对；0011 只建立个人密文表，不导入任何 Token。应用不自动建表或迁移。
2. 在服务器受保护的进程环境或私有环境配置文件设置 `RUNTU_TELEGRAM_BINDING_ENABLED=true`。为个人 Bot 另设 `RUNTU_NOTIFICATION_ENCRYPTION_KEYS`，内容为一到四个逗号分隔的 Fernet 密钥，新密钥在前、无空格。维护人员可在受保护、不会录屏或保存输出的终端使用 `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 生成，将输出直接送入受控 secret storage，勿贴入网页、聊天、仓库或日志。与数据库备份分离保管；丢失所有解密密钥无法恢复 Token。
3. 正确配置认证数据库和 HTTPS `RUNTU_AUTH_ORIGIN`；仅受控本地开发可使用已有 loopback 例外。按维护授权流程激活服务，本应用不会自动修改环境或重启。浏览器 GET 配置成功、personal_available=true 才能绑定个人 Bot；没有共享 Bot Token 也能使用个人模式。
4. 公共 Bot 额外由 owner/维护人员在服务端设 `RUNTU_TELEGRAM_BOT_TOKEN`、匹配的 `RUNTU_TELEGRAM_BOT_USERNAME`、独立高熵 32–256 字符 URL-safe `RUNTU_TELEGRAM_WEBHOOK_SECRET`。通过 Telegram 官方 API 为正确外部 HTTPS origin 的 `/api/telegram/webhook` 配置 secret_token。独立回调密钥不得复用 Bot Token 或放进 URL；反向代理需可信 HTTPS scheme 与匹配 Host。网页“平台公共 Bot 管理”只展示就绪/缺失布尔状态及清单，不读取或修改服务器秘密。
5. 用授权的测试账户完成两种模式各自的 Start→候选→确认→选择私聊→保存启用→测试→断开验收。真实 Token/Telegram 发送属于独立授权，不是本次模拟测试的一部分。

### 密钥轮换

先在操作员环境把新 Fernet 密钥放第一位，保留旧解密密钥；按授权激活后，账户本人或 owner 在选定账户使用“用当前密钥重新加密”（POST rotate-secret）。服务端验证所属账户封套后重加密，不返回明文；同一 Bot/身份/偏好保持不变。确认**每个已存密文**都已轮换，并在隔离验证及备份策略允许后，才移除旧密钥。不能仅因一个账户成功就删旧密钥；错误删除会令未轮换账户不可用。Token 本身更换须重新验证并清空绑定，这是另一种操作。

## API、限流与回滚

GET/PUT 基础路径；POST choose-public/connect/confirm/disconnect/test/sync-personal/rotate-secret 只接收 expected_revision。choose-personal 仅接收 token、exclusive=true 和 expected_revision。PUT 接收 enabled、private_target、四个固定事件布尔值、expected_revision。拒绝任意 query、额外 user_id/chat_id/URL 等字段；所有浏览器写入要求会话、Origin/CSRF。个人 Token 验证每发起者 5 次/五分钟、全局 30；同步 10/60；保留原配对/测试/发送限流。

GET `/api/admin/notifications/platform` 仅 owner，返回 feature_enabled/public_ready/token_present/username_present/webhook_secret_present/encryption_ready；不返回配置值。所有 GET/写响应 no-store，平台状态不开放给 admin/viewer。

保留单个 16 项 best-effort 队列、事件/收件人持久化去重、当前角色/启用/私聊目标/绑定版本复核、五分钟事件期限、固定 TLS sendMessage、无重定向/代理、socket 超时和三秒测试 API 截止。个人控制 API 固定 api.telegram.org，方法白名单和 64 KiB 请求/响应上限，不打印上游诊断。socket 超时不是整个网络调用的硬实时保证；同步租约过期的结果不能提交。无历史重试或送达保证。

0011 降级必须先断开所有个人 Bot 并删除密文；跨 0010 降级还检查全部 Bot 选择/目标/挑战及早期旧单例、待审核保护，拒绝时不先删除表。只在临时 SQLite 和 CI PostgreSQL 验证。

## 验证与后续

个人模式集成测试模拟 getMe、getWebhookInfo、getUpdates 与发送，覆盖完整私聊/测试/解绑、跨账户加密隔离、Bot 唯一性、缺失密钥、轮换、公共回调不能消费个人挑战、Origin/CSRF、owner/IDOR、角色/账户撤销、过期/重放/租约竞争和迁移保护。Node 验证敏感字段拒绝与 owner 路径；浏览器 API 全拦截，验证 Token 成功/失败后清空、重试、个人全流程、公共流程保留、owner 次要入口、部署状态与键盘/1440/390/360。

[当前界面截图](ui/TASK-0054/README.md)。历史 TASK-0052/0053 部分里程碑不能作为当前能力说明。群组/多个目标和对应成员校验、逐目标去重仍需正式后续任务，本任务不自动创建或执行下一任务。

官方依据：[Telegram getMe](https://core.telegram.org/bots/api#getme)、[getUpdates](https://core.telegram.org/bots/api#getupdates)、[getWebhookInfo](https://core.telegram.org/bots/api#getwebhookinfo)、[Deep linking](https://core.telegram.org/bots/features#deep-linking)、[Fernet/MultiFernet](https://cryptography.io/en/stable/fernet/)。依赖许可在 [licenses/telegram](licenses/telegram/README.md)。
