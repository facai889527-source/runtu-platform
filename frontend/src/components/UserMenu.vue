<script setup>
import { computed, ref, onMounted, onUnmounted, useTemplateRef } from 'vue'
import { logout } from '../api/auth.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ identity: Object, access: Object, pending: Boolean, unavailable: Boolean })
const emit = defineEmits(['signed-out', 'refresh-identity'])
const busy = ref(false), error = ref('')
const disclosure = useTemplateRef('disclosure')
const names = { owner: '所有者', admin: '管理员', viewer: '普通用户' }
const role = computed(() => props.access.data.value ? names[props.access.data.value.role] : '')
const avatar = computed(() => props.identity?.user?.username?.slice(0, 1).toUpperCase() || '')
let controller, timer
function close(event) {
  if (!disclosure.value?.open) return
  if (event.type === 'keydown') {
    if (event.key !== 'Escape') return
    disclosure.value.open = false
    disclosure.value.querySelector('summary')?.focus()
  } else if (!disclosure.value.contains(event.target)) disclosure.value.open = false
}
async function signOut() {
  if (busy.value) return
  busy.value = true; error.value = ''; controller = new AbortController()
  timer = setTimeout(() => controller.abort(), 10000)
  try {
    const result = await logout(controller.signal)
    if (result.authenticated) throw new Error('Logout not confirmed')
    emit('signed-out')
  } catch {
    error.value = '退出未确认，请检查连接后重试。'
    emit('refresh-identity')
  } finally { clearTimeout(timer); busy.value = false }
}
onMounted(() => { document.addEventListener('pointerdown', close); document.addEventListener('keydown', close) })
onUnmounted(() => {
  clearTimeout(timer); controller?.abort()
  document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close)
})
</script>

<template>
  <span v-if="pending" class="account-status" role="status">确认身份…</span>
  <div v-else-if="unavailable" class="account-unavailable"><span role="status">身份暂无法确认</span><button @click="$emit('refresh-identity')">重试</button></div>
  <details v-else-if="identity?.authenticated" ref="disclosure" class="user-menu">
    <summary class="user-trigger" aria-label="账户菜单"><span class="user-avatar" aria-hidden="true">{{ avatar }}</span><span class="user-name">{{ identity.user.username }}</span><AppIcon name="right" :size="14" /></summary>
    <div class="user-popover">
      <p class="account-name">{{ identity.user.username }}</p>
      <p v-if="role" class="account-role">{{ role }}</p>
      <p v-else-if="access.pending.value" class="account-role" role="status">正在确认角色…</p>
      <div v-else class="account-role"><p role="status">角色暂无法确认</p><button @click="access.load()">重试角色查询</button></div>
      <p class="account-note">账户设置尚未开放</p>
      <button class="sign-out" :disabled="busy" @click="signOut">{{ busy ? '正在退出…' : '退出登录' }}</button>
    </div>
  </details>
  <p v-if="error" class="account-error" role="alert">{{ error }}</p>
</template>

<style scoped>
.account-status, .account-unavailable { font-size: 12px; color: var(--muted); }
.account-unavailable { display: flex; align-items: center; gap: 8px; }
.user-menu { position: relative; min-width: 0; }
.user-trigger { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 2px 8px 2px 2px; cursor: pointer; border-radius: 8px; list-style: none; }
.user-trigger::-webkit-details-marker { display: none; }
.user-trigger:hover, .user-menu[open] .user-trigger { background: var(--canvas); }
.user-menu[open] .user-trigger>.app-icon { transform: rotate(90deg); }
.user-avatar { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--accent-soft); color: var(--accent); font-weight: 650; flex-shrink: 0; }
.user-name { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.user-popover { position: absolute; top: calc(100% + 10px); right: 0; z-index: 10; width: min(260px, calc(100vw - 32px)); padding: 18px; background: var(--surface); border: 1px solid var(--line); border-radius: 10px; box-shadow: 0 10px 30px #142e3818; }
.account-name { font-weight: 650; overflow-wrap: anywhere; margin-bottom: 4px; }
.account-role { color: var(--accent); font-size: 13px; margin-bottom: 16px; }
.account-note { color: var(--muted); border-top: 1px solid var(--line); padding-top: 14px; font-size: 12px; }
.sign-out { width: 100%; color: var(--danger); }
.account-error { color: var(--danger); font-size: 12px; width: 100%; margin: 0; }
@media (max-width: 760px) { .user-name { max-width: 80px; } }
</style>
