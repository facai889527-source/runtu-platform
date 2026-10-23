<script setup>
import { shallowRef,computed,onUnmounted } from 'vue'
import { updateUser } from '../api/users.js'
import UserDialog from './UserDialog.vue'
import UserModuleAccess from './UserModuleAccess.vue'
import { roleLabel } from '../utils/userDirectory.js'
const props=defineProps({user:{type:Object,required:true},selfId:String})
const emit=defineEmits(['updated','close'])
const current=shallowRef({...props.user}),role=shallowRef(props.user.role),active=shallowRef(props.user.active),tab=shallowRef('account'),busy=shallowRef(false),grantsBusy=shallowRef(false),confirm=shallowRef(false),error=shallowRef(''),message=shallowRef('')
const self=computed(()=>current.value.id===props.selfId),changed=computed(()=>role.value!==current.value.role||active.value!==current.value.active)
let controller,timer
function requestSave(){if(!busy.value&&!self.value&&changed.value){confirm.value=true;error.value='';message.value=''}}
async function save(){
 if(busy.value||self.value||!confirm.value||!changed.value)return
 busy.value=true;controller=new AbortController();timer=setTimeout(()=>controller.abort(),10000)
 try{const value=await updateUser(current.value.id,{role:role.value,active:active.value,expected_role:current.value.role,expected_active:current.value.active},controller.signal);current.value=value;role.value=value.role;active.value=value.active;message.value='账户变更已保存。';confirm.value=false;emit('updated',value)}
 catch(cause){error.value=cause.name==='AbortError'?'保存结果未确认，请关闭后刷新列表检查。':cause.message;confirm.value=false}
 finally{busy.value=false;clearTimeout(timer)}
}
function tabKey(event){if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();tab.value=event.key==='Home'?'account':event.key==='End'?'tools':tab.value==='account'?'tools':'account';event.currentTarget.parentElement.querySelector('#'+(tab.value==='account'?'account':'tools')+'-tab').focus()}}
onUnmounted(()=>{controller?.abort();clearTimeout(timer)})
</script>
<template>
<UserDialog :title="current.username" description="管理账户资料与工具访问权限。" :busy="busy||grantsBusy" @close="emit('close')">
<div class="user-tabs" role="tablist" aria-label="用户管理分类">
<button id="account-tab" role="tab" :aria-selected="tab==='account'" :tabindex="tab==='account'?0:-1" aria-controls="account-panel" :disabled="busy||grantsBusy" @click="tab='account'" @keydown="tabKey">账户资料</button>
<button id="tools-tab" role="tab" :aria-selected="tab==='tools'" :tabindex="tab==='tools'?0:-1" aria-controls="tools-panel" :disabled="busy||grantsBusy" @click="tab='tools'" @keydown="tabKey">工具授权</button>
</div>
<section v-if="tab==='account'" id="account-panel" role="tabpanel" aria-labelledby="account-tab" tabindex="0">
<form class="user-form user-update-form" @submit.prevent="requestSave">
<p v-if="self" class="user-guidance">这是您当前使用的账户，不能更改自身角色或停用自身。所有者保护由服务端校验。</p>
<fieldset :disabled="busy||self||confirm">
<legend class="sr-only">管理 {{current.username}}</legend>
<label>角色<select v-model="role" class="user-select">
<option value="viewer">普通用户</option>
<option value="admin">管理员</option>
<option value="owner">所有者</option>
</select>
<small>不会允许停用或降级最后一位已启用的所有者。</small>
</label>
<label class="user-toggle">
<input v-model="active" type="checkbox" role="switch" :aria-checked="active" />
<span>
<strong>启用账户</strong>
<small>停用后无法登录；已有会话会被撤销。</small>
</span>
</label>
</fieldset>
<dl class="user-metadata">
<div>
<dt>创建日期</dt>
<dd>{{new Date(current.created_at).toLocaleString('zh-CN',{hour12:false})}}</dd>
</div>
</dl>
<details class="user-advanced">
<summary>高级账户信息</summary>
<p>账户标识 <span>{{current.id}}</span>
</p>
</details>
<div v-if="confirm" class="user-confirm" role="group" aria-label="确认账户变更">
<p>将角色设为「{{roleLabel(role)}}」、账户{{active?'启用':'停用'}}。保存会撤销此账户已有会话。</p>
<div>
<button type="button" :disabled="busy" @click="confirm=false">返回编辑</button>
<button class="user-primary" type="button" :disabled="busy" @click="save">{{busy?'正在保存…':'确认保存'}}</button>
</div>
</div>
<p v-if="error" class="user-form-error" role="alert">{{error}}</p>
<p v-if="message" class="user-success" role="status">{{message}}</p>
<footer class="user-dialog-actions">
<button type="button" :disabled="busy" @click="emit('close')">关闭</button>
<button v-if="!confirm" class="user-primary" type="submit" :disabled="busy||self||!changed">保存变更</button>
</footer>
</form>
</section>
<section v-else id="tools-panel" role="tabpanel" aria-labelledby="tools-tab" tabindex="0">
<UserModuleAccess :user-id="current.id" :active="current.active" @busy="grantsBusy=$event" />
</section>
</UserDialog>
</template>
<style scoped>
.user-tabs{display:flex;gap:24px;border-bottom:1px solid var(--line);margin:-8px 0 24px}.user-tabs button{border:0;border-bottom:2px solid transparent;border-radius:0;color:var(--muted);padding:14px 0;background:transparent}.user-tabs button[aria-selected=true]{color:var(--accent);border-bottom-color:var(--accent)}.user-metadata{margin:0;font-size:12px}.user-metadata>div{display:flex;gap:16px;justify-content:space-between}.user-metadata dt{color:var(--muted)}.user-metadata dd{margin:0}.user-advanced{font-size:12px;color:var(--muted)}.user-advanced summary{cursor:pointer;min-height:32px}.user-advanced p{font-size:12px;margin:8px 0 0}.user-advanced span{display:block;overflow-wrap:anywhere}.user-success{color:var(--accent);margin:0;font-size:13px}
</style>
