<script setup>
import { ref, useTemplateRef, onUnmounted } from 'vue'
import { createUser } from '../api/users.js'
const emit = defineEmits(['created'])
const username = ref(''), role = ref('viewer'), busy = ref(false), error = ref(''), success = ref('')
const passwordInput = useTemplateRef('passwordInput')
let controller, timer
async function submit() {
  if (busy.value) return
  if (role.value !== 'viewer' && !window.confirm('此角色将获得管理权限。确认创建？')) { passwordInput.value.value = ''; return }
  const password = passwordInput.value.value
  passwordInput.value.value = ''
  busy.value = true; error.value = ''; success.value = ''
  controller = new AbortController(); timer = setTimeout(() => controller.abort(), 10000)
  try {
    const value = await createUser(username.value, password, role.value, controller.signal)
    username.value = ''; role.value = 'viewer'; success.value = '用户已创建。初始密码不会再次显示。'
    emit('created', value)
  } catch (cause) { error.value = cause.name === 'AbortError' ? '创建结果未确认，请先刷新列表，避免重复创建。' : cause.message }
  finally { clearTimeout(timer); busy.value = false; if (passwordInput.value) passwordInput.value.value = '' }
}
onUnmounted(() => { controller?.abort(); clearTimeout(timer); if (passwordInput.value) passwordInput.value.value = '' })
</script>
<template>
  <section class="panel user-create" aria-labelledby="create-user-title">
    <h2 id="create-user-title">创建用户</h2><p class="subtle">默认角色为只读成员。初始密码请通过安全渠道交给本人，提交后立即清空。</p>
    <form class="user-create-form" @submit.prevent="submit" :aria-busy="busy">
      <fieldset :disabled="busy"><legend class="sr-only">新用户资料</legend>
        <label>用户名<input v-model="username" required minlength="3" maxlength="64" pattern="[a-z0-9_.\-]{3,64}" autocomplete="off" /></label>
        <label>初始密码<input ref="passwordInput" type="password" required minlength="14" maxlength="128" autocomplete="new-password" /></label>
        <label>角色<select v-model="role"><option value="viewer">只读成员 · viewer</option><option value="admin">管理员 · admin</option><option value="owner">所有者 · owner</option></select></label>
      </fieldset><button type="submit" :disabled="busy">{{ busy ? '正在创建…' : '创建用户' }}</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p><p v-if="success" role="status">{{ success }}</p>
  </section>
</template>
<style scoped>
.user-create { padding: 24px; }
.user-create-form fieldset { border: 0; padding: 0; margin: 20px 0; display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 16px; }
label { display: grid; gap: 8px; } input, select { width: 100%; min-width: 0; min-height: 44px; }
button { min-height: 44px; } [role=alert] { color: var(--danger); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); }
@media(max-width: 760px) { .user-create-form fieldset { grid-template-columns: 1fr; } .user-create { padding: 20px; } }
</style>
