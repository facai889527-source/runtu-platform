<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { readUserModules, saveUserModule } from '../api/moduleAccess.js'
import { useResource } from '../composables/useResource.js'
const props=defineProps({userId:{type:String,required:true},active:Boolean})
const open=ref(false), after=ref(null), previous=ref([]),busy=ref(false),error=ref(''),message=ref('')
const grants=useResource(readUserModules)
let controller,timer,live=true
function load(){grants.load(props.userId,after.value)}
function first(){after.value=null;previous.value=[];load()}
function next(){const cursor=grants.data.value?.next_after_module;if(cursor!=null){previous.value.push(after.value);after.value=cursor;load()}}
function back(){if(previous.value.length){after.value=previous.value.pop();load()}}
watch(open,value=>{if(value&&props.active)first();else{grants.cancel();grants.data.value=null}})
watch(()=>props.userId,()=>{open.value=false;grants.cancel();grants.data.value=null;controller?.abort()})
async function toggle(row,event){
  const granted=!row.granted
  event.target.checked=row.granted
  if(busy.value||!window.confirm(`确认${granted?'授予':'撤销'}此用户的「${row.name}」使用授权？`))return
  busy.value=true;error.value='';message.value='';controller=new AbortController();timer=setTimeout(()=>controller.abort(),10000)
  const userId=props.userId
  try{await saveUserModule(userId,row.module_id,{granted,expected_granted:row.granted},controller.signal);if(!live||userId!==props.userId)return;message.value='工具授权已保存。';window.dispatchEvent(new Event('runtu-tools-changed'));if(open.value)await grants.load(userId,after.value)}
  catch(cause){if(live&&userId===props.userId)error.value=cause.name==='AbortError'?'结果未确认，请刷新授权后检查。':cause.message}
  finally{busy.value=false;clearTimeout(timer)}
}
onUnmounted(()=>{live=false;grants.cancel();controller?.abort();clearTimeout(timer)})
</script>
<template>
  <div class="user-module-access">
    <button type="button" :aria-expanded="open" @click="open=!open">业务工具授权</button>
    <div v-if="open" class="grant-content">
      <p class="subtle">只控制明确声明为受保护业务工具的使用权，不授予平台管理权限。</p>
      <p v-if="!active" role="status">账户已禁用，请先启用账户后再管理授权。</p>
      <template v-else>
        <button type="button" :disabled="busy||grants.pending.value" @click="first">刷新授权</button>
        <p v-if="grants.pending.value" role="status">正在加载工具授权…</p>
        <div v-else-if="grants.error.value" role="alert"><p>{{grants.error.value.message}}</p><button @click="load">重试授权查询</button></div>
        <template v-else-if="grants.data.value">
          <p v-if="!grants.data.value.items.length" class="subtle">当前没有可授权的受保护业务工具。公开演示工具无需授权。</p>
          <ul v-else class="grant-items"><li v-for="row in grants.data.value.items" :key="row.module_id"><label><input type="checkbox" :checked="row.granted" :disabled="busy" @change="toggle(row,$event)" />{{row.name}} <span class="subtle">{{row.module_id}}{{row.enabled?'':' · 平台已禁用，授权不会生效'}}</span></label></li></ul>
        </template>
        <p v-if="error" role="alert">{{error}}</p><p v-if="message" role="status">{{message}}</p>
        <nav aria-label="授权分页"><button :disabled="busy||grants.pending.value||!previous.length" @click="back">上一页授权</button><button :disabled="busy||grants.pending.value||grants.data.value?.next_after_module==null" @click="next">下一页授权</button></nav>
      </template>
    </div>
  </div>
</template>
<style scoped>
.user-module-access{margin-top:16px}.grant-content{border-left:3px solid var(--accent);padding:4px 16px;margin-top:12px}.grant-items{list-style:none;padding:0}.grant-items li{padding:10px 0}label{display:flex;gap:10px;align-items:center;flex-wrap:wrap}input{width:18px;min-height:18px;accent-color:var(--accent)}button{min-height:44px}nav{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}[role=alert]{color:var(--danger)}
</style>
