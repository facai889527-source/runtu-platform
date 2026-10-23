<script setup>
import { computed,ref,watch,onUnmounted } from 'vue'
import { readUsers } from '../api/users.js'
import { readTelegramPlatform } from '../api/notifications.js'
import AccountSelect from '../components/AccountSelect.vue'
import NotificationSettings from '../components/NotificationSettings.vue'
import TelegramSetup from '../components/TelegramSetup.vue'
const props=defineProps({access:Object,selfId:String})
const owner=computed(()=>props.access?.data.value?.role==='owner')
const target=ref(''),accounts=ref([]),next=ref(null),pending=ref(false),error=ref(''),managerOpen=ref(false),platformOpen=ref(false),platform=ref(null),platformError=ref('')
const options=computed(()=>[{value:'',label:'我的消息'},...accounts.value.filter(u=>u.id!==props.selfId).map(u=>({value:u.id,label:u.username+(u.active?'':'（已禁用）')}))])
const targetName=computed(()=>accounts.value.find(u=>u.id===target.value)?.username||'所选账户')
let controller,platformController,generation=0
async function load(after=null){
 controller?.abort();controller=new AbortController();const id=++generation;pending.value=true;error.value=''
 try{const page=await readUsers(after,controller.signal);if(id===generation){accounts.value=page.items;next.value=page.next_after_username;target.value=''}}
 catch(e){if(id===generation&&e.name!=='AbortError')error.value=e.message}
 finally{if(id===generation)pending.value=false}
}
function managerToggle(event){managerOpen.value=event.target.open;if(event.target.open&&owner.value&&!accounts.value.length)load()}
async function platformToggle(event){
 platformOpen.value=event.target.open;if(!event.target.open||!owner.value)return
 platformController?.abort();platformController=new AbortController();platformError.value=''
 try{platform.value=await readTelegramPlatform(platformController.signal)}catch(e){if(e.name!=='AbortError')platformError.value=e.message}
}
watch(owner,()=>{target.value='';managerOpen.value=false;platformOpen.value=false;generation++;controller?.abort();platformController?.abort();accounts.value=[];platform.value=null;pending.value=false})
onUnmounted(()=>{generation++;controller?.abort();platformController?.abort()})
</script>
<template>
 <section class="notifications-page" aria-labelledby="notifications-title">
  <div class="notification-heading"><div><h2 id="notifications-title">{{target?'账户消息':'消息设置'}}</h2><p>{{target?'正在管理 '+targetName+' 的 Telegram 配置':'让重要消息，抵达你的 Telegram。'}}</p></div><span>Telegram 专属</span></div>
  <div v-if="target" class="target-context"><strong>{{targetName}}</strong><button type="button" @click="target=''">返回我的设置</button></div>
  <NotificationSettings :key="target" :target="target" :owner="owner" />
  <aside v-if="owner" class="owner-tools" aria-label="所有者管理">
   <p class="owner-caption">所有者管理</p>
   <details class="platform-telegram" @toggle="platformToggle"><summary><span>平台公共 Bot 管理<small>检查服务端状态与启用清单</small></span><span aria-hidden="true">＋</span></summary><div v-if="platformOpen" class="owner-panel"><p v-if="platformError" role="alert">{{platformError}}</p><div v-if="platform" class="platform-status"><span>通知功能 <b>{{platform.feature_enabled?'已启用':'未启用'}}</b></span><span>公共 Bot <b>{{platform.public_ready?'已就绪':'待配置'}}</b></span><span>Token <b>{{platform.token_present?'已设置':'未设置'}}</b></span><span>Bot 用户名 <b>{{platform.username_present?'已设置':'未设置'}}</b></span><span>回调密钥 <b>{{platform.webhook_secret_present?'已设置':'未设置'}}</b></span><span>加密存储 <b>{{platform.encryption_ready?'已就绪':'待配置'}}</b></span></div><TelegramSetup owner /></div></details>
   <details class="notification-manager" @toggle="managerToggle"><summary><span>管理其他账户<small>仅所有者可读写其他账户的消息配置</small></span><span aria-hidden="true">＋</span></summary><div v-if="managerOpen" class="owner-panel"><AccountSelect v-model="target" :options="options" label="选择消息配置所属账户" :disabled="pending" /><p v-if="pending" role="status">正在读取账户…</p><p v-if="error" role="alert">{{error}}</p><div v-if="next" class="manager-pages"><span>当前为已加载批次</span><button type="button" :disabled="pending" @click="load(next)">更多账户</button></div><button v-if="!next&&accounts.length>=20" type="button" :disabled="pending" @click="load()">返回首批账户</button></div></details>
  </aside>
 </section>
</template>
<style scoped>
.notifications-page{max-width:940px;margin:0 auto;min-width:0}.notification-heading{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:22px}.notification-heading h2{font-size:24px;font-weight:650;letter-spacing:-.03em;margin:0 0 8px}.notification-heading p{color:var(--muted);font-size:13px;line-height:1.7;margin:0}.notification-heading>span{font-size:11px;color:var(--accent);background:#e7f1ef;padding:6px 10px;border-radius:6px;white-space:nowrap}.owner-tools{margin-top:24px}.owner-caption{font-size:11px;color:var(--muted);margin:0 0 8px}.owner-tools details{border-bottom:1px solid #dde5e8}.owner-tools summary{display:flex;justify-content:space-between;align-items:center;gap:16px;cursor:pointer;padding:15px 4px;min-height:44px;list-style:none;font-size:13px}.owner-tools summary::-webkit-details-marker{display:none}.owner-tools summary small{display:block;font-size:11px;color:var(--muted);margin-top:5px}.owner-tools summary>span:last-child{font-size:20px;color:var(--muted)}.owner-panel{padding:4px 0 20px}.owner-panel>p{font-size:12px;color:var(--muted);line-height:1.8}.platform-status{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:14px 0 20px;font-size:11px;color:var(--muted)}.platform-status b{display:block;color:var(--ink);font-weight:550;margin-top:5px}.manager-pages{display:flex;align-items:center;justify-content:space-between;margin-top:12px;font-size:11px;color:var(--muted)}.manager-pages button,.target-context button{min-height:44px;font-size:12px}.target-context{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px;background:#eaf3f0;padding:10px 16px;border-radius:10px;font-size:13px}.target-context strong{overflow-wrap:anywhere}@media(max-width:600px){.notification-heading{align-items:flex-start;margin-bottom:18px}.notification-heading h2{font-size:22px}.notification-heading>span{font-size:10px;padding:5px 8px}.platform-status{grid-template-columns:repeat(2,1fr)}.target-context{padding:10px 12px}}
</style>
