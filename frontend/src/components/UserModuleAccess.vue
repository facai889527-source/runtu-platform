<script setup>
import { shallowRef,watch,onUnmounted } from 'vue'
import { readUserModules,saveUserModule } from '../api/moduleAccess.js'
import { useResource } from '../composables/useResource.js'
const props=defineProps({userId:{type:String,required:true},active:Boolean})
const emit=defineEmits(['busy'])
const after=shallowRef(null),previous=shallowRef([]),busy=shallowRef(false),error=shallowRef(''),message=shallowRef(''),confirmation=shallowRef(null)
const grants=useResource(readUserModules)
let controller,timer,live=true
function load(){confirmation.value=null;error.value='';message.value='';grants.load(props.userId,after.value)}
function first(){after.value=null;previous.value=[];load()}
function next(){const cursor=grants.data.value?.next_after_module;if(cursor!=null){previous.value=[...previous.value,after.value];after.value=cursor;load()}}
function back(){if(previous.value.length){const pages=[...previous.value];after.value=pages.pop();previous.value=pages;load()}}
watch(()=>[props.userId,props.active],()=>{controller?.abort();grants.cancel();grants.data.value=null;confirmation.value=null;message.value='';if(props.active)first()},{immediate:true})
async function save(){
 const row=confirmation.value;if(!row||busy.value||!props.active)return
 busy.value=true;emit('busy',true);error.value='';message.value='';controller=new AbortController();timer=setTimeout(()=>controller.abort(),10000)
 const userId=props.userId
 try{await saveUserModule(userId,row.module_id,{granted:!row.granted,expected_granted:row.granted},controller.signal);if(!live||userId!==props.userId)return;confirmation.value=null;message.value='工具授权已保存。';window.dispatchEvent(new Event('runtu-tools-changed'));await grants.load(userId,after.value)}
 catch(cause){if(live&&userId===props.userId){error.value=cause.name==='AbortError'?'结果未确认，请刷新授权后检查。':cause.message;confirmation.value=null}}
 finally{busy.value=false;emit('busy',false);clearTimeout(timer)}
}
onUnmounted(()=>{live=false;grants.cancel();controller?.abort();clearTimeout(timer)})
</script>
<template>
<div class="user-module-access">
<p class="grant-intro">按工具分配使用权，不授予平台管理权限。公开演示工具无需授权。</p>
<p v-if="!active" class="user-guidance" role="status">账户已禁用，请先启用账户后再管理授权。</p>
<template v-else>
<div class="grant-toolbar">
<h3>业务工具</h3>
<button :disabled="busy||grants.pending.value" @click="first">刷新授权</button>
</div>
<p v-if="grants.pending.value" role="status">正在加载工具授权…</p>
<div v-else-if="grants.error.value" class="user-form-error" role="alert">
<p>{{grants.error.value.message}}</p>
<button @click="load">重试授权查询</button>
</div>
<template v-else-if="grants.data.value">
<p v-if="!grants.data.value.items.length" class="grant-empty">当前没有可授权的业务工具。</p>
<ul v-else class="grant-items">
<li v-for="row in grants.data.value.items" :key="row.module_id">
<div>
<strong>{{row.name}}</strong>
<small>{{row.enabled?(row.granted?'已授权使用':'尚未授权'):'平台已停用，授权暂不生效'}}</small>
</div>
<button :disabled="busy||!!confirmation" :aria-label="`${row.granted?'撤销':'授予'} ${row.name} 授权`" :class="{'grant-revoke':row.granted}" @click="confirmation=row">{{row.granted?'撤销授权':'授予访问'}}</button>
</li>
</ul>
</template>
<div v-if="confirmation" class="user-confirm" role="group" aria-label="确认工具授权">
<p>确认{{confirmation.granted?'撤销':'授予'}}「{{confirmation.name}}」使用授权？</p>
<div>
<button :disabled="busy" @click="confirmation=null">取消</button>
<button class="user-primary" :disabled="busy" @click="save">{{busy?'正在保存…':'确认授权变更'}}</button>
</div>
</div>
<p v-if="error" class="user-form-error" role="alert">{{error}}</p>
<p v-if="message" class="user-success" role="status">{{message}}</p>
<nav v-if="previous.length||grants.data.value?.next_after_module!=null" class="grant-pagination" aria-label="授权分页">
<button :disabled="busy||grants.pending.value||!previous.length" @click="back">上一页授权</button>
<button :disabled="busy||grants.pending.value||grants.data.value?.next_after_module==null" @click="next">下一页授权</button>
</nav>
</template>
</div>
</template>
<style scoped>
.grant-intro{font-size:13px;color:var(--muted);margin-bottom:20px}.grant-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px}.grant-toolbar h3{margin:0}.grant-toolbar button{font-size:12px;border:0;color:var(--accent)}.grant-items{margin-bottom:20px}.grant-items li{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 0;border-bottom:1px solid var(--line)}.grant-items li>div{min-width:0}.grant-items strong{font-size:14px;overflow-wrap:anywhere}.grant-items small{display:block;font-size:12px;line-height:1.8;margin-top:4px}.grant-items button{font-size:12px;flex-shrink:0;color:var(--accent);background:var(--accent-soft);border-color:transparent}.grant-items button.grant-revoke{background:white;color:var(--muted);border-color:var(--line)}.grant-pagination{display:flex;justify-content:space-between;gap:10px;margin-top:20px}.grant-empty{padding:28px 0;color:var(--muted);text-align:center;font-size:13px}.user-success{color:var(--accent);font-size:13px;margin:12px 0 0}
</style>
