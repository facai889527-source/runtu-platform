<script setup>
import { ref, onUnmounted } from 'vue'
import RouteLink from './RouteLink.vue'
import { logout } from '../api/auth.js'
defineProps({ identity: Object, pending: Boolean, unavailable: Boolean })
const emit = defineEmits(['changed'])
const busy = ref(false), error = ref('')
let controller, timer
async function signOut() {
  if (busy.value) return
  busy.value = true; error.value = ''; controller = new AbortController()
  timer = setTimeout(() => controller.abort(), 10000)
  try { await logout(controller.signal) }
  catch { error.value = '退出未确认，请检查连接后重试。' }
  finally { clearTimeout(timer); busy.value = false; emit('changed') }
}
onUnmounted(() => { clearTimeout(timer); controller?.abort() })
</script>
<template>
  <div class="identity-bar" aria-label="身份状态">
    <span role="status">{{ pending ? '正在确认身份…' : unavailable ? '身份暂无法确认 · 公开只读浏览' : identity?.authenticated ? `已登录 · ${identity.user.username} · 当前只读` : '匿名浏览 · 当前只读' }}</span>
    <button v-if="identity?.authenticated && !unavailable && !pending" :disabled="busy" @click="signOut">{{ busy ? '正在退出…' : '退出登录' }}</button>
    <RouteLink v-else to="/login" class="button-link">管理员登录</RouteLink>
    <p v-if="error" role="alert">{{ error }}</p>
  </div>
</template>
<style scoped>
.identity-bar { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); padding: 0 0 16px; margin: 20px 0 24px; font-size: 14px; color: #455d69; }
.identity-bar span { overflow-wrap: anywhere; min-width: 0; }
.identity-bar p { width: 100%; color: var(--danger); margin: 0; }
</style>
