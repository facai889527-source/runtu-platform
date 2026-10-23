<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PolicySwitch from './PolicySwitch.vue'
import { readNotifications, saveNotifications, testNotifications } from '../api/notifications.js'

const current = ref(null), enabled = ref(false), chat = ref(''), registration = ref(false)
const busy = ref(false), error = ref(''), message = ref(''), cooldown = ref(false)
const dirty = computed(() => current.value && (enabled.value !== current.value.enabled || chat.value !== current.value.chat_id || registration.value !== current.value.events.registration))
const chatValid = computed(() => chat.value === '' || (/^-?[1-9][0-9]{0,18}$/.test(chat.value) && Math.abs(Number(chat.value)) < 2**52))
const canSave = computed(() => dirty.value && chatValid.value && (!enabled.value || (current.value?.token_configured && chat.value !== '')))
const canTest = computed(() => current.value?.enabled && current.value.token_configured && current.value.chat_id && !dirty.value && !cooldown.value)
let controller, timer, cooldownTimer, live = true
function adopt(value) { current.value = value; enabled.value = value.enabled; chat.value = value.chat_id; registration.value = value.events.registration }
async function operation(action = 'read') {
  if (busy.value) return
  busy.value = true; error.value = ''; message.value = ''
  controller = new AbortController(); timer = setTimeout(() => controller.abort(), 8000)
  try {
    if (action === 'test') {
      await testNotifications(current.value.revision, controller.signal)
      if (live) message.value = 'Telegram 已确认测试消息发送成功。'
    } else {
      const value = action === 'save' ? await saveNotifications({ enabled: enabled.value, chat_id: chat.value,
        events: { registration: registration.value, account_security: false, tool_outcomes: false, system_errors: false }, expected_revision: current.value.revision }, controller.signal) : await readNotifications(controller.signal)
      if (live) { adopt(value); if (action === 'save') message.value = '消息设置已保存。' }
    }
  } catch (cause) {
    if (live) {
      error.value = cause.name === 'AbortError' ? '结果未确认，请刷新设置；测试消息请勿立即重发。' : cause.message
      if ([401, 403].includes(cause.status)) current.value = null
    }
  } finally {
    clearTimeout(timer)
    if (live) {
      busy.value = false
      if (action === 'test') { cooldown.value = true; cooldownTimer = setTimeout(() => { cooldown.value = false }, 300000) }
    }
  }
}
onMounted(() => operation())
onUnmounted(() => { live = false; controller?.abort(); clearTimeout(timer); clearTimeout(cooldownTimer) })
</script>

<template>
  <div class="notification-settings" :aria-busy="busy">
    <div class="notification-section-heading"><h3>Telegram</h3><button type="button" :disabled="busy" @click="operation()">刷新设置</button></div>
    <p v-if="busy" role="status" class="notification-feedback">正在处理消息设置…</p>
    <p v-if="error" role="alert" class="notification-error">{{ error }}</p>
    <p v-if="message" role="status" class="notification-success">{{ message }}</p>
    <form v-if="current" @submit.prevent="operation('save')">
      <fieldset :disabled="busy" class="notification-fields"><legend class="visually-hidden">Telegram 连接与通知偏好</legend>
        <PolicySwitch v-model="enabled" label="启用 Telegram 通知" description="仅在保存并配置完整后，向指定会话发送已支持的事件。" :disabled="!current.token_configured && !enabled" />
        <div class="notification-connection">
          <div class="notification-secret"><strong>Bot Token</strong><span class="notification-token-state">{{ current.token_configured ? '•••••••• · 已配置' : '未配置' }}</span><p>由服务端环境变量 RUNTU_TELEGRAM_BOT_TOKEN 管理，此页面不接收或显示密钥。请联系平台维护人员配置。</p></div>
          <label class="notification-chat" for="telegram-chat">Chat ID<input id="telegram-chat" v-model="chat" type="text" inputmode="text" autocomplete="off" maxlength="21" placeholder="例如 -1001234567890" :aria-invalid="!chatValid" aria-describedby="telegram-chat-help" /><small id="telegram-chat-help">填写数字会话 ID，可带负号。机器人需已加入目标会话并有发送权限。</small></label>
        </div>
        <div class="notification-section-heading event-heading"><h3>通知事件</h3><span>仅发送必要摘要</span></div>
        <PolicySwitch v-model="registration" label="注册申请" description="需要审核的新申请提交成功后发送；不包含申请人、密码或 IP。" />
        <PolicySwitch :model-value="false" disabled label="账户安全与重要变更" description="暂不可用：尚未接入专用通知事件源。" />
        <PolicySwitch :model-value="false" disabled label="工具任务结果" description="暂不可用：平台尚无统一任务结果事件源。" />
        <PolicySwitch :model-value="false" disabled label="系统错误" description="暂不可用：尚未接入脱敏、聚合后的错误事件源。" />
        <p class="notification-delivery-note">通知按尽力发送处理，不重试历史事件；队列满或发送失败时可能丢弃，注册仍正常完成。</p>
        <div class="notification-actions"><span>{{ dirty ? '有未保存的更改' : '当前设置已同步' }}</span><button type="submit" class="notification-save" :disabled="!canSave">保存消息设置</button></div>
      </fieldset>
    </form>
    <div v-if="current" class="notification-test"><div><strong>检查连接</strong><p>{{ cooldown ? '已尝试发送，请五分钟后再试。' : dirty ? '请先保存更改，再向已保存的会话发送测试消息。' : !canTest ? '配置 Token、Chat ID 并保存启用后可测试。' : '发送一条测试消息。平台每五分钟最多尝试一次。' }}</p></div><button type="button" :disabled="busy || !canTest" @click="operation('test')">发送测试消息</button></div>
  </div>
</template>

<style scoped>
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.notification-section-heading{display:flex;justify-content:space-between;align-items:center;gap:16px}.notification-section-heading h3{font-size:15px;margin:0;font-weight:600}.notification-section-heading>span{font-size:12px;color:var(--muted)}.notification-settings button{min-height:44px;padding:0 16px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:inherit;font-size:13px;cursor:pointer}.notification-settings button:disabled{opacity:.5;cursor:not-allowed}.notification-fields{border:0;margin:0;padding:0;min-width:0}.notification-connection{padding:24px 0 30px;display:grid;grid-template-columns:1fr 1fr;gap:28px}.notification-secret{display:grid;align-content:start;gap:10px}.notification-secret strong,.notification-chat{font-size:13px;font-weight:550}.notification-token-state{font-size:13px;color:var(--accent)}.notification-secret p,.notification-chat small,.notification-delivery-note,.notification-test p{font-size:12px;font-weight:400;color:var(--muted);line-height:1.8;margin:0;overflow-wrap:anywhere}.notification-chat{display:grid;align-content:start;gap:10px}.notification-chat input{width:100%;min-width:0;box-sizing:border-box;min-height:44px;border:1px solid var(--line);background:var(--surface);color:var(--ink);border-radius:8px;padding:10px 12px;font:inherit;font-size:14px}.notification-chat input[aria-invalid=true]{border-color:var(--danger)}.event-heading{padding-top:20px;border-top:1px solid var(--line)}.notification-delivery-note{margin:18px 0;max-width:70ch}.notification-actions{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:8px 0 26px}.notification-actions>span{font-size:12px;color:var(--muted)}.notification-actions .notification-save{background:var(--accent);color:white;border-color:var(--accent)}.notification-test{border-top:1px solid var(--line);padding:24px 0;display:flex;align-items:center;justify-content:space-between;gap:24px}.notification-test strong{font-size:13px}.notification-test p{margin-top:8px}.notification-test button{flex-shrink:0}.notification-feedback,.notification-error,.notification-success{font-size:13px;line-height:1.8;margin:16px 0}.notification-error{color:var(--danger)}.notification-success{color:var(--accent)}@media(max-width:600px){.notification-connection{grid-template-columns:1fr;gap:24px;padding-bottom:24px}.notification-test{align-items:stretch;flex-direction:column;gap:16px}.notification-actions{align-items:stretch;flex-direction:column;gap:12px}.notification-actions>span{align-self:flex-start}.notification-settings :deep(.policy-switch){gap:16px}}
</style>
