<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { updateUser } from '../api/users.js'
import UserModuleAccess from './UserModuleAccess.vue'
const props = defineProps({ user: { type: Object, required: true }, selfId: String })
const emit = defineEmits(['updated'])
const role = ref('viewer'), active = ref(true), busy = ref(false), error = ref(''), success = ref('')
watch(() => props.user, value => { role.value = value.role; active.value = value.active; error.value = ''; success.value = '' }, { immediate: true })
let controller, timer
async function submit() {
  if (busy.value) return
  if (!window.confirm(`确认修改 ${props.user.username} 的角色或状态？已有会话将被撤销。`)) return
  busy.value = true; error.value = ''; success.value = ''
  controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try {
    const value = await updateUser(props.user.id, { role: role.value, active: active.value, expected_role: props.user.role, expected_active: props.user.active }, controller.signal)
    success.value = '修改已保存。'; emit('updated', value)
  } catch (cause) { error.value = cause.name === 'AbortError' ? '保存结果未确认，请刷新列表后检查。' : cause.message }
  finally { clearTimeout(timer); busy.value = false }
}
onUnmounted(() => { controller?.abort(); clearTimeout(timer) })
</script>
<template>
  <li class="managed-user">
    <div class="managed-user-heading"><h3>{{ user.username }}</h3><span v-if="user.id === selfId" class="subtle">当前账户 · 受保护</span><span>{{ user.active ? '已启用' : '已禁用' }}</span></div>
    <details class="account-details"><summary>账户详情</summary><p class="subtle user-id">{{ user.id }}</p><p class="subtle">创建于 <time :datetime="user.created_at">{{ new Date(user.created_at).toLocaleString('zh-CN', { hour12: false }) }}</time></p></details>
    <form class="user-update-form" @submit.prevent="submit" :aria-busy="busy"><fieldset :disabled="busy || user.id === selfId"><legend class="sr-only">管理 {{ user.username }}</legend>
      <label>角色<select v-model="role"><option value="viewer">只读成员 · viewer</option><option value="admin">管理员 · admin</option><option value="owner">所有者 · owner</option></select></label>
      <label class="user-active"><input v-model="active" type="checkbox" />启用账户</label>
      <button type="submit" :disabled="busy || (role === user.role && active === user.active)">保存变更</button>
    </fieldset></form><p v-if="error" role="alert">{{ error }}</p><p v-if="success" role="status">{{ success }}</p>
    <UserModuleAccess :user-id="user.id" :active="user.active" />
  </li>
</template>
<style scoped>
.managed-user { border-top: 1px solid var(--line); padding: 18px 0; }
.managed-user-heading { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; } h3 { margin: 0; }
.account-details { margin: 12px 0; color: var(--muted); font-size: 12px; } .account-details summary { cursor: pointer; min-height: 44px; padding: 12px 0; } .user-id { overflow-wrap: anywhere; font-size: 12px; }
fieldset { border: 0; padding: 0; display: flex; gap: 16px; align-items: end; flex-wrap: wrap; } label { display: grid; gap: 8px; } select, button { min-height: 44px; }
.user-active { display: flex; align-items: center; min-height: 44px; gap: 8px; } .user-active input { width: 18px; min-height: 18px; accent-color: var(--accent); }
[role=alert] { color: var(--danger); } .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media(max-width:760px) { fieldset { display:grid; grid-template-columns: 1fr 1fr; gap:12px; align-items:center; } fieldset>label:first-of-type { grid-column:1/-1; } .user-active { font-size:13px; } }
</style>
