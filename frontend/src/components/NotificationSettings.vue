<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import PolicySwitch from './PolicySwitch.vue'
import { readNotifications, saveNotifications, testNotifications, connectTelegram, confirmTelegram, disconnectTelegram, choosePublicBot } from '../api/notifications.js'

const props=defineProps({target:{type:String,default:''}})
const privateTarget=ref(false)
const current=ref(null), enabled=ref(false), registration=ref(false), link=ref('')
const busy=ref(false), error=ref(''), message=ref(''), cooldown=ref(false)
const dirty=computed(()=>current.value && (enabled.value!==current.value.enabled || registration.value!==current.value.events.registration || privateTarget.value!==current.value.private_target))
const canSave=computed(()=>dirty.value && (!enabled.value || (current.value.available && current.value.bound && privateTarget.value)))
const canTest=computed(()=>current.value?.available && current.value.bound && current.value.enabled && !dirty.value && !cooldown.value)
watch(privateTarget,value=>{if(!value)enabled.value=false})
let controller,timer,cooldownTimer,live=true
function adopt(v){current.value=v;enabled.value=v.enabled;registration.value=v.events.registration;privateTarget.value=v.private_target;if(v.bound||v.pairing.state==='none')link.value=''}
async function operation(action='read') {
  if(busy.value)return
  busy.value=true;error.value='';message.value=''
  controller=new AbortController();timer=setTimeout(()=>controller.abort(),8000)
  try {
    if(action==='test'){await testNotifications(current.value.revision,controller.signal,props.target);if(live)message.value='Telegram 已确认测试消息发送成功。'}
    else if(action==='connect') {
      const pairing=await connectTelegram(current.value.revision,controller.signal,props.target)
      if(live)link.value=pairing.url
      const v=await readNotifications(controller.signal,props.target);if(live)adopt(v)
    } else {
      const v=action==='save'?await saveNotifications({enabled:enabled.value,private_target:privateTarget.value,events:{registration:registration.value,account_security:false,tool_outcomes:false,system_errors:false},expected_revision:current.value.revision},controller.signal,props.target)
        :action==='choose-public'?await choosePublicBot(current.value.revision,controller.signal,props.target)
        :action==='confirm'?await confirmTelegram(current.value.revision,controller.signal,props.target)
        :action==='disconnect'?await disconnectTelegram(current.value.revision,controller.signal,props.target):await readNotifications(controller.signal,props.target)
      if(live){adopt(v);if(action!=='read')message.value={'choose-public':'已选择公共 Bot。接下来验证 Telegram 身份。',save:'消息设置已保存。',confirm:'Telegram 已验证并连接，请选择偏好后保存启用。',disconnect:'Telegram 已断开，配对链接和排队旧消息已失效。'}[action]}
    }
  }catch(cause){if(live){error.value=cause.name==='AbortError'?'结果未确认，请刷新；测试消息请勿立即重发。':cause.message;if([401,403].includes(cause.status)){current.value=null;link.value=''}}}
  finally{clearTimeout(timer);if(live){busy.value=false;if(action==='test'){cooldown.value=true;cooldownTimer=setTimeout(()=>{cooldown.value=false},300000)}}}
}
onMounted(()=>operation())
onUnmounted(()=>{live=false;controller?.abort();clearTimeout(timer);clearTimeout(cooldownTimer);link.value=''})
</script>

<template>
  <div class="notification-settings" :aria-busy="busy">
    <div class="notification-section-heading"><h3>Telegram 连接</h3><button type="button" :disabled="busy" @click="operation()">检查连接状态</button></div>
    <p v-if="busy" role="status" class="notification-feedback">正在处理个人消息设置…</p>
    <p v-if="error" role="alert" class="notification-error">{{ error }}</p>
    <p v-if="message" role="status" class="notification-success">{{ message }}</p>
    <template v-if="current">
      <div class="telegram-binding">
        <strong class="binding-state">{{ current.bound ? '已验证连接 '+current.destination : '尚未连接 Telegram' }}</strong>
        <p v-if="props.target" class="manager-note">正在管理指定账户。选择、重新配对或断开会撤销该账户的旧路由。配对需由目标 Telegram 身份完成，并由当前管理会话确认。</p>
        <div v-if="!current.bot_mode" class="bot-choices">
          <div><strong>公共 Bot</strong><p>由平台维护。主动选择后，仍需私聊验证和选择接收目标。</p><button class="choose-public" type="button" :disabled="busy || !current.public_available" @click="operation('choose-public')">使用公共 Bot</button></div>
          <div><strong>个人 Bot</strong><p>个人 Bot、群组发现与多目标路由尚未开放。本阶段不会收集 Token。</p><button type="button" disabled>绑定个人 Bot（暂不可用）</button></div>
        </div>
        <p v-else>已选择公共 Bot。当前阶段支持一个经验证、主动选择的 Telegram 私聊目标。</p>
        <p v-if="!current.public_available" class="binding-unavailable">平台机器人尚未开放配对。请联系维护人员完成安全回调配置。</p>
        <p v-if="current.bot_mode && !current.available && current.public_available" class="notification-error">公共 Bot 配置已变化，旧连接已停止投递。请断开后重新选择并验证。</p>
        <p v-if="current.paused" class="notification-error">上次发送失败，通知已暂停。请确认未屏蔽机器人，再保存启用。</p>
        <div v-if="current.bot_mode" class="binding-actions"><button class="telegram-connect" type="button" :disabled="busy || !current.available" @click="operation('connect')">{{ current.bound ? '重新连接 Telegram' : '连接 Telegram' }}</button><button v-if="current.bot_mode" class="telegram-disconnect" type="button" :disabled="busy" @click="operation('disconnect')">断开并撤销配对</button></div>
        <p v-if="current.bound" class="binding-note">重新连接会立即停用并取消旧绑定，验证后需要重新保存启用。</p>
        <div v-if="current.pairing.state!=='none'" class="telegram-pairing" role="region" aria-label="Telegram 配对步骤">
          <ol><li>打开下方一次性链接，仅在{{props.target?'目标账户使用的':'自己的'}} Telegram 中点击 Start。</li><li>返回此页，点击“检查连接状态”。</li><li>确认刚才由自己的 Telegram 完成操作，再在网页确认绑定。</li></ol>
          <a v-if="link" class="telegram-pair-link" :href="link" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer">在 Telegram 中配对</a>
          <p v-else>如尚未点击 Start，请重新连接以生成新链接。</p>
          <p class="binding-note">链接五分钟有效、仅能使用一次。不要分享链接或让他人代为配对；退出登录后需重新生成。</p>
          <p v-if="current.pairing.state==='confirm'" class="pairing-candidate">待确认身份 {{ current.pairing.candidate }}。仅在确认刚才由自己的 Telegram 完成操作时继续。</p>
          <button v-if="current.pairing.state==='confirm'" class="telegram-confirm" type="button" :disabled="busy" @click="operation('confirm')">{{props.target?'确认目标 Telegram':'确认我的 Telegram'}}</button>
        </div>
      </div>
      <p v-if="current.bound" class="target-chip">已验证身份 {{ current.destination }} · 私聊目标 {{ current.private_target?'已选择':'未选择' }}</p>
      <form @submit.prevent="operation('save')"><fieldset :disabled="busy" class="notification-fields"><legend class="visually-hidden">个人通知偏好</legend>
        <PolicySwitch v-model="privateTarget" label="选择已验证私聊" description="主动选择此目标后才能启用。取消选择并保存会撤销排队投递。" :disabled="!current.available || !current.bound" />
        <PolicySwitch v-model="enabled" :label="props.target?'启用此账户通知':'启用我的通知'" description="仅向此配置已验证、主动选择的 Telegram 私聊发送通知。" :disabled="(!current.available || !current.bound || !privateTarget) && !enabled" />
        <div class="notification-section-heading event-heading"><h3>通知事件</h3><span>个人订阅</span></div>
        <PolicySwitch v-model="registration" label="注册申请" :disabled="!current.supported.registration" :description="current.supported.registration ? '仅所有者或管理员可订阅；收到需审核的新申请时提醒。' : '仅所有者或管理员可订阅。普通用户不会收到注册提醒。'" />
        <PolicySwitch :model-value="false" disabled label="账户安全与重要变更" description="暂不可用：尚未接入专用通知事件源。" />
        <PolicySwitch :model-value="false" disabled label="我的工具任务结果" description="暂不可用：尚无真实任务结果事件源；不会订阅他人的工具活动。" />
        <PolicySwitch :model-value="false" disabled label="系统错误" description="暂不可用：尚未接入安全的聚合错误事件源。" />
        <p class="notification-delivery-note">尽力投递，失败可能丢弃且不重试历史事件。发送失败会暂停个人通知，业务操作不受影响。</p>
        <div class="notification-actions"><span>{{ dirty?'有未保存的更改':'个人偏好已同步' }}</span><button type="submit" class="notification-save" :disabled="!canSave">保存个人偏好</button></div>
      </fieldset></form>
      <div class="notification-test"><div><strong>{{props.target?'测试此账户连接':'测试我的连接'}}</strong><p>{{ cooldown?'已尝试发送，请五分钟后再试。':dirty?'请先保存更改。':!canTest?'验证绑定、选择私聊并保存启用后可测试。':'只向本人已验证会话发送一条测试消息，每五分钟最多一次。' }}</p></div><button type="button" :disabled="busy || !canTest" @click="operation('test')">发送测试消息</button></div>
    </template>
  </div>
</template>

<style scoped>
.visually-hidden{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.notification-section-heading{display:flex;justify-content:space-between;align-items:center;gap:16px}.notification-section-heading h3{font-size:15px;margin:0;font-weight:600}.notification-section-heading>span{font-size:12px;color:var(--muted)}.notification-settings button{min-height:44px;padding:0 16px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:inherit;font-size:13px;cursor:pointer}.notification-settings button:disabled{opacity:.5;cursor:not-allowed}.notification-fields{border:0;margin:0;padding:0;min-width:0}.event-heading{padding-top:20px;border-top:1px solid var(--line)}.notification-delivery-note,.notification-test p{font-size:12px;line-height:1.8;color:var(--muted)}.notification-delivery-note{margin:18px 0;max-width:70ch}.notification-actions{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:8px 0 26px}.notification-actions>span{font-size:12px;color:var(--muted)}.notification-actions .notification-save{background:var(--accent);color:white;border-color:var(--accent)}.notification-test{border-top:1px solid var(--line);padding:24px 0;display:flex;align-items:center;justify-content:space-between;gap:24px}.notification-test strong{font-size:13px}.notification-test p{margin-top:8px}.notification-test button{flex-shrink:0}.notification-feedback,.notification-error,.notification-success{font-size:13px;line-height:1.8;margin:16px 0}.notification-error{color:var(--danger)}.notification-success{color:var(--accent)}@media(max-width:600px){.notification-test{align-items:stretch;flex-direction:column;gap:16px}.notification-actions{align-items:stretch;flex-direction:column;gap:12px}.notification-actions>span{align-self:flex-start}.notification-settings :deep(.policy-switch){gap:16px}}
.bot-choices{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin:24px 0}.bot-choices>div{border-top:2px solid var(--line);padding-top:18px}.bot-choices strong{font-size:14px}.target-chip{display:inline-block;padding:8px 12px;border-radius:6px;background:var(--accent-soft);font-size:12px;overflow-wrap:anywhere}.manager-note{border-left:3px solid var(--accent);padding-left:12px}@media(max-width:600px){.bot-choices{grid-template-columns:1fr;gap:18px}}
.telegram-binding{padding:24px 0;border-bottom:1px solid var(--line)}.binding-state{font-size:15px}.telegram-binding p,.telegram-pairing li{font-size:12px;line-height:1.9;color:var(--muted);max-width:70ch}.binding-actions{display:flex;flex-wrap:wrap;gap:12px;margin:20px 0 10px}.binding-actions .telegram-connect,.telegram-confirm{background:var(--accent);color:white;border-color:var(--accent)}.telegram-pairing{border-left:3px solid var(--accent);padding:4px 0 4px 20px;margin-top:24px}.telegram-pairing ol{padding-left:18px}.telegram-pair-link{display:inline-flex;min-height:44px;align-items:center;color:var(--accent);font-size:14px;font-weight:550}.notification-settings .telegram-binding .notification-error{color:var(--danger)}@media(max-width:600px){.binding-actions{display:grid}.telegram-pairing{padding-left:14px}}
</style>
