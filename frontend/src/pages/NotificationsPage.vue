<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
import { readUsers } from '../api/users.js'
import AccountSelect from '../components/AccountSelect.vue'
import NotificationSettings from '../components/NotificationSettings.vue'
const props=defineProps({access:Object})
const owner=computed(()=>props.access?.data.value?.role==='owner')
const target=ref(''),accounts=ref([]),next=ref(null),pending=ref(false),error=ref('')
const options=computed(()=>[{value:'',label:'我的消息'},...accounts.value.map(u=>({value:u.id,label:u.username+(u.active?'':'（已禁用）')}))])
let controller,generation=0
async function load(after=null){
  controller?.abort();controller=new AbortController();const id=++generation;pending.value=true;error.value=''
  try{const page=await readUsers(after,controller.signal);if(id===generation){accounts.value=page.items;next.value=page.next_after_username;target.value=''}}
  catch(e){if(id===generation&&e.name!=='AbortError')error.value=e.message}
  finally{if(id===generation)pending.value=false}
}
watch(owner,value=>{target.value='';if(value)load();else{generation++;controller?.abort();accounts.value=[];pending.value=false}}, {immediate:true})
onUnmounted(()=>{generation++;controller?.abort()})
</script>

<template>
  <section class="notifications-page" aria-labelledby="notifications-title">
    <div class="notification-heading"><h2 id="notifications-title">{{ target?'账户消息':'我的消息' }}</h2><p>{{ target?'管理所选账户的 Telegram 连接和接收偏好。':'连接自己的 Telegram，独立选择接收的通知。' }}</p></div>
    <div v-if="owner" class="notification-manager">
      <h3>账户消息管理</h3><p>仅所有者可管理其他账户的 Telegram 设置。列表每页最多 20 个账户。</p>
      <AccountSelect v-model="target" :options="options" label="选择消息配置所属账户" :disabled="pending" />
      <p v-if="error" role="alert">{{ error }}</p><p v-if="pending" role="status">正在读取账户…</p>
      <div class="manager-pages"><button type="button" :disabled="pending" @click="load()">回到首批账户</button><button type="button" :disabled="pending || !next" @click="load(next)">下一批账户</button></div>
    </div>
    <NotificationSettings :key="target" :target="target" />
  </section>
</template>

<style scoped>
.notification-manager{border-bottom:1px solid var(--line);padding-bottom:24px;margin-bottom:24px}.notification-manager h3{font-size:15px}.notification-manager p{font-size:12px;color:var(--muted);line-height:1.8}.manager-pages{display:flex;gap:12px;margin-top:12px}.manager-pages button{min-height:44px;font-size:12px}
.notifications-page{max-width:860px}.notification-heading{margin-bottom:28px}.notification-heading h2{font-size:22px;letter-spacing:-.02em;margin:0 0 8px}.notification-heading p{color:var(--muted);font-size:13px;line-height:1.8;margin:0}
</style>
