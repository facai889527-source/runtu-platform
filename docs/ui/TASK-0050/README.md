# TASK-0050 Telegram 消息设置

沿用当前认证后外壳、Segoe UI / Microsoft YaHei UI、浅灰画布 #f5f7f9、白色输入 #ffffff、墨色 #223641、辅助色 #60717c、青绿 #087363、分隔 #e3e9ed。标题 22px、章节 15px、字段 13–14px、帮助 12px。左对齐的单列设置流，以连接、事件、测试的真实职责分隔；桌面连接区域两列，手机自然变为一列。保留大量横向呼吸，不使用外框卡片、重复统计或提供方选择器。

设计复核后保留现有视觉语言：唯一提供方 Telegram 已足够明确，连接状态直接呈现，无额外装饰性图标或摘要卡。路由页面仅负责构成，NotificationSettings 管理草稿和请求生命周期，复用 PolicySwitch；服务端权限是唯一授权来源。

以下 13 张图片全部由本地 Chrome 和完全拦截的隔离 API 夹具生成；未接触真实账户、密钥、会话或数据库，也没有向 Telegram 发送网络请求。Bot Token 只显示固定掩码和配置状态，页面没有密钥输入字段。

| 场景 | 1440×900 | 390×844 | 360×800 |
| --- | --- | --- | --- |
| 连接设置 | [查看](notifications-configured-1440.png) | [查看](notifications-configured-390.png) | [查看](notifications-configured-360.png) |
| 事件与测试操作（滚动后） | [查看](notifications-events-1440.png) | [查看](notifications-events-390.png) | [查看](notifications-events-360.png) |
| 后端确认的测试成功 | [查看](notifications-sent-1440.png) | [查看](notifications-sent-390.png) | [查看](notifications-sent-360.png) |

附加：[未配置](notifications-unconfigured-1440.png)、[测试失败](notifications-send-failure-360.png)、[管理员访问](notifications-admin-360.png)、[普通用户禁止访问](notifications-viewer-denied-360.png)。

视觉检查：下方事件区与操作区滚动可达，文字自然换行，无横向溢出；开关保留 44px 点击区域和键盘焦点，灰色不可用类别有文字解释。现有手机外壳的标题换行保持一致，本任务未重做顶栏。全局设置旧审核迁移提示、链接元素及占用间距已完全移除。

验证：Node 36 项；Vite 89 模块生产构建；Python 全量 174 项通过、11 项独立 PostgreSQL 用例本地跳过（另有一个既存依赖警告）；最终传输保密性专项验证见 PR。完整 Chrome 回归和消息专项通过，包含保存、无效 Chat ID、未配置禁用、键盘 Space 开关、真实确认成功／失败、冲突、服务不可用、owner/admin/viewer/匿名访问以及原用户/审核/授权/工具流程。

服务端支持与限制见 [消息设置说明](../../NOTIFICATIONS.md)。真实数据库未执行 0008，后端未重启，新接口和真实 Telegram 投递尚未启用；这些图片只证明 UI 的隔离验证结果。当前提交 CI 结果见 PR28。
