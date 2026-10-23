<script setup>
import { shallowRef,onUnmounted } from 'vue'
import { useResource } from '../composables/useResource.js'
import { readApplication,approve,reject } from '../api/registration.js'
import UserDialog from './UserDialog.vue'
const props=defineProps({applicationId:{type:String,required:true}}),emit=defineEmits(['close','reviewed'])
const detail=useResource(readApplication),busy=shallowRef(false),decision=shallowRef(''),error=shallowRef('')
let controller,timer
function load(){decision.value='';error.value='';detail.load(props.applicationId)}
load()
async function save(){
 if(busy.value||!decision.value||detail.data.value?.state!=='pending')return
 busy.value=true;error.value='';controller=new AbortController();timer=setTimeout(()=>controller.abort(),10000)
 try{const result=await(decision.value==='approve'?approve:reject)(props.applicationId,controller.signal);emit('reviewed',result.state)}
 catch(cause){error.value=cause.name==='AbortError'?'审核结果未确认，请刷新详情后检查，避免重复操作。':cause.message;decision.value=''}
 finally{busy.value=false;clearTimeout(timer)}
}
onUnmounted(()=>{detail.cancel();controller?.abort();clearTimeout(timer)})
</script>
<template>
<UserDialog :title="detail.data.value?.username||'注册申请'" description="注册审核仅决定是否允许此申请成为普通用户账户。" :busy="busy" @close="emit('close')">
<p v-if="detail.pending.value" role="status">正在核实申请状态…</p>
<div v-else-if="detail.error.value" class="user-form-error" role="alert"><p>{{detail.error.value.message}}</p><button @click="load">刷新申请详情</button></div>
<div v-else-if="detail.data.value" class="review-detail">
<span class="application-state" :class="detail.data.value.state">{{detail.data.value.state==='pending'?'待审核':detail.data.value.state==='rejected'?'已拒绝':'已批准'}}</span>
<dl><div><dt>申请用户名</dt><dd>{{detail.data.value.username}}</dd></div><div><dt>提交时间</dt><dd>{{new Date(detail.data.value.created_at).toLocaleString('zh-CN',{hour12:false})}}</dd></div><div><dt>批准后角色</dt><dd>普通用户</dd></div></dl>
<p class="user-guidance">申请尚未获批前无法登录，不属于已启用账户。批准前请通过独立渠道核实申请人身份；工具访问需要另行授权。</p>
<p v-if="detail.data.value.state!=='pending'" class="review-finished">此申请已完成审核，不能再次改变审核决定。请刷新列表查看最新状态。</p>
<div v-if="decision" class="user-confirm" role="group" aria-label="确认注册审核"><p>{{decision==='approve'?'确认已核实申请人身份，批准为普通用户？批准不会授予业务工具。':'确认拒绝此申请？此决定不能撤回，申请人将保持无法登录。'}}</p><div><button :disabled="busy" @click="decision=''">返回</button><button :class="decision==='reject'?'review-danger':'user-primary'" :disabled="busy" @click="save">{{busy?'正在处理…':decision==='approve'?'确认批准':'确认拒绝'}}</button></div></div>
<p v-if="error" class="user-form-error" role="alert">{{error}}</p>
<footer class="user-dialog-actions"><button :disabled="busy" @click="load">刷新详情</button><template v-if="detail.data.value.state==='pending'&&!decision"><button class="review-danger" @click="decision='reject'">拒绝申请</button><button class="user-primary" @click="decision='approve'">批准申请</button></template><button v-else-if="!decision" @click="emit('close')">关闭</button></footer>
</div>
</UserDialog>
</template>
<style scoped>
.review-detail{display:grid;gap:20px}.review-detail dl{margin:0;display:grid;gap:16px;font-size:13px}.review-detail dl>div{display:flex;justify-content:space-between;gap:20px}.review-detail dt{color:var(--muted);flex-shrink:0}.review-detail dd{margin:0;overflow-wrap:anywhere;text-align:right}.review-finished{font-size:13px;color:var(--muted);margin:0}.review-danger{color:var(--danger);border-color:#e8c2bd}.user-dialog-actions{flex-wrap:wrap}.application-state{justify-self:start}.review-detail :deep(.user-guidance){font-size:12px}
@media(max-width:600px){.user-dialog-actions>button:first-child{flex-basis:100%;order:2;border-color:transparent;color:var(--muted);min-height:36px}.user-dialog-actions>button:not(:first-child){min-width:100px}}
</style>
