<script setup>
import { shallowRef,useTemplateRef,onUnmounted } from 'vue'
import { createUser } from '../api/users.js'
import UserDialog from './UserDialog.vue'
const emit=defineEmits(['created','close'])
const username=shallowRef(''),role=shallowRef('viewer'),busy=shallowRef(false),error=shallowRef(''),elevated=shallowRef(false),passwordInput=useTemplateRef('passwordInput')
let controller,timer
async function submit(){
 if(busy.value)return
 if(role.value!=='viewer'&&!elevated.value){error.value='请确认此账户需要管理权限。';return}
 const password=passwordInput.value.value;passwordInput.value.value=''
 busy.value=true;error.value='';controller=new AbortController();timer=setTimeout(()=>controller.abort(),10000)
 try{emit('created',await createUser(username.value,password,role.value,controller.signal))}
 catch(cause){error.value=cause.name==='AbortError'?'创建结果未确认，请关闭后刷新列表，避免重复创建。':cause.message}
 finally{clearTimeout(timer);busy.value=false;if(passwordInput.value)passwordInput.value.value=''}
}
onUnmounted(()=>{controller?.abort();clearTimeout(timer);if(passwordInput.value)passwordInput.value.value=''})
</script>
<template>
<UserDialog title="新建用户" description="为新成员创建账户，按职责分配初始角色。" :busy="busy" @close="emit('close')">
<form class="user-form user-create-form" @submit.prevent="submit">
<fieldset :disabled="busy">
<legend class="sr-only">新用户资料</legend>
<label>用户名<input v-model="username" autofocus required minlength="3" maxlength="64" pattern="[a-z0-9_.\-]{3,64}" autocomplete="off" />
<small>3–64 位小写字母、数字或 _ . -</small>
</label>
<label>初始密码<input ref="passwordInput" type="password" required minlength="14" maxlength="128" autocomplete="new-password" />
<small>14–128 位，提交后立即清空，不会再次显示。</small>
</label>
<label>角色<select v-model="role" class="user-select" @change="elevated=false">
<option value="viewer">普通用户</option>
<option value="admin">管理员</option>
<option value="owner">所有者</option>
</select>
<small>普通用户仅能访问获授权工具；管理角色拥有额外权限。</small>
</label>
<label v-if="role!=='viewer'" class="user-toggle">
<input v-model="elevated" type="checkbox" required />我已核实此账户需要管理权限</label>
</fieldset>
<p class="user-guidance">请通过安全渠道将初始密码交给本人。不要在聊天、截图或公开记录中分享密码。</p>
<p v-if="error" class="user-form-error" role="alert">{{error}}</p>
<footer class="user-dialog-actions">
<button type="button" :disabled="busy" @click="emit('close')">取消</button>
<button class="user-primary" type="submit" :disabled="busy">{{busy?'正在创建…':'创建用户'}}</button>
</footer>
</form>
</UserDialog>
</template>
