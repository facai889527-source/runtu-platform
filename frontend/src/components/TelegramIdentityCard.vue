<script setup>
import { shallowRef } from 'vue'
defineProps({identity:Object,pending:Boolean})
const copied=shallowRef('')
async function copy(label,value){try{await navigator.clipboard.writeText(value);copied.value=label+'已复制'}catch{copied.value='复制未成功，请选中编号复制'}}
</script>
<template>
 <div class="identity-card" :class="{pending}">
  <template v-if="identity"><div class="identity-heading"><span class="identity-avatar" aria-hidden="true">{{identity.display_name.slice(0,1)}}</span><div><strong>{{identity.display_name}}</strong><span>{{identity.username?'@'+identity.username:'未设置 Telegram 用户名'}}</span></div><span class="identity-proof">{{pending?'待核对':'已验证'}}</span></div>
  <dl><div><dt>Telegram User ID</dt><dd><span>{{identity.user_id}}</span><button type="button" :aria-label="'复制 Telegram User ID '+identity.user_id" @click="copy('User ID',identity.user_id)">复制</button></dd></div><div><dt>私聊 Chat ID</dt><dd><span>{{identity.chat_id}}</span><button type="button" :aria-label="'复制私聊 Chat ID '+identity.chat_id" @click="copy('Chat ID',identity.chat_id)">复制</button></dd></div></dl><p v-if="copied" role="status">{{copied}}</p></template>
  <p v-else class="identity-missing">已保留现有连接。完整身份详情将在服务更新后提供，无需现在断开或重新绑定。</p>
 </div>
</template>
<style scoped>
.identity-card{min-width:0}.identity-heading{display:flex;align-items:center;gap:12px;margin-bottom:14px}.identity-avatar{width:38px;height:38px;display:grid;place-items:center;background:#e8f2f0;color:var(--accent);border-radius:50%;font-weight:600;flex-shrink:0}.identity-heading>div{min-width:0;flex:1}.identity-heading strong{display:block;font-size:14px;overflow-wrap:anywhere}.identity-heading>div>span{display:block;font-size:11px;color:var(--muted);margin-top:4px;overflow-wrap:anywhere}.identity-proof{font-size:10px;color:var(--accent);white-space:nowrap}.pending .identity-proof{color:#866117}dl{margin:0;display:grid;gap:8px}dl>div{display:flex;align-items:center;justify-content:space-between;gap:12px}dt{font-size:11px;color:var(--muted)}dd{margin:0;display:flex;gap:10px;align-items:center;font-size:12px;font-variant-numeric:tabular-nums;min-width:0}dd>span{overflow-wrap:anywhere}button{min-height:36px;border:0;background:transparent;color:var(--accent);font-size:11px;cursor:pointer}button:focus-visible{outline:3px solid var(--focus);outline-offset:2px}p{font-size:11px;color:var(--muted);line-height:1.7}.identity-missing{margin:0}
@media(max-width:380px){dl>div{align-items:flex-start;flex-direction:column;gap:0}dd{width:100%;justify-content:space-between}}
</style>
