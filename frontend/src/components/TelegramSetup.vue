<script setup>
defineProps({owner:Boolean})
</script>
<template>
  <div class="telegram-setup">
    <h4>在哪里配置？</h4>
    <ol>
      <li><strong>部署并迁移后端</strong><span>由维护人员部署包含个人 Bot 接口的版本。备份并获得授权后，在服务器项目根目录执行 <code>python -m alembic upgrade head</code>，确认到 <code>0011_personal_telegram_bot</code>。0010 会清除旧绑定，需重新配对。</span></li>
      <li><strong>启用与加密存储</strong><span>在服务器环境或受保护的环境配置文件设置 <code>RUNTU_TELEGRAM_BINDING_ENABLED=true</code> 和 <code>RUNTU_NOTIFICATION_ENCRYPTION_KEYS</code>。密钥由操作员在受保护终端生成 Fernet 密钥并保管，多个密钥以逗号分隔、新密钥在前；不要填到网页或提交仓库。配置后由维护人员按授权流程激活服务。</span></li>
      <li><strong>选择一种 Bot</strong><span>个人 Bot：在 Telegram 的 BotFather 创建专用 Bot，把 Token 输入上方“绑定个人 Bot”，验证后在私聊点击 Start，再回来同步、确认并启用。个人 Bot 不需要平台 webhook；已有 webhook 或其他部署占用时会拒绝绑定，不会接管。</span><span>公共 Bot：操作员另外配置 <code>RUNTU_TELEGRAM_BOT_TOKEN</code>、<code>RUNTU_TELEGRAM_BOT_USERNAME</code>、独立 <code>RUNTU_TELEGRAM_WEBHOOK_SECRET</code> 和正确的 HTTPS <code>RUNTU_AUTH_ORIGIN</code>；通过 Telegram 官方 API 设置 <code>/api/telegram/webhook</code> 与 secret_token。页面不展示这些密钥。</span></li>
    </ol>
    <p>{{owner?'你可以查看下方平台状态，但网页不会修改服务器环境或自动迁移、重启。':'如你不管理服务器，请把这份清单交给平台所有者。'}} 当前仅支持已验证私聊；群组与多目标尚未开放。</p>
  </div>
</template>
<style scoped>
.telegram-setup{padding:20px;background:#f0f6f5;border-radius:12px;color:var(--ink)}h4{margin:0 0 16px;font-size:14px}ol{margin:0;padding-left:20px;display:grid;gap:18px}li{padding-left:4px;font-size:12px;line-height:1.9}strong,span{display:block}strong{font-size:13px;margin-bottom:4px}span,p{color:var(--muted)}p{font-size:12px;line-height:1.8;margin:18px 0 0}code{font-size:11px;overflow-wrap:anywhere;word-break:break-word;background:#e3eeeb;padding:2px 4px;border-radius:3px}
</style>
