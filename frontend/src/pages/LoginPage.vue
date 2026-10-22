<script setup>
import { ref, onUnmounted } from 'vue'
import RouteLink from '../components/RouteLink.vue'
import { login } from '../api/auth.js'
const emit = defineEmits(['authenticated'])
const username = ref(''), password = ref(''), pending = ref(false), error = ref('')
let controller, timer
async function submit() {
  if (pending.value) return
  pending.value = true; error.value = ''
  controller = new AbortController()
  timer = setTimeout(() => controller.abort(), 10000)
  // Clear the bound field immediately; no credential persistence or logging.
  const operation = login(username.value, password.value, controller.signal)
  password.value = ''
  try {
    const result = await operation
    if (!result.authenticated) throw new Error('未能确认登录状态，请重试。')
    emit('authenticated')
  } catch (failure) {
    error.value = failure.name === 'AbortError' ? '请求超时，请重新确认登录状态后重试。' : failure.message || '网络连接失败，请稍后重试。'
  } finally { clearTimeout(timer); pending.value = false }
}
onUnmounted(() => { clearTimeout(timer); controller?.abort(); password.value = '' })
</script>
<template>
  <section class="login-panel" aria-labelledby="login-title">
    <div class="login-context"><h1 id="login-title">登录管理后台</h1><p>使用你的平台账户继续。</p></div>
    <form class="login-form" @submit.prevent="submit" :aria-busy="pending">
      <label for="login-username">用户名</label>
      <input id="login-username" v-model="username" name="username" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64" :disabled="pending" />
      <label for="login-password">密码</label>
      <input id="login-password" v-model="password" name="password" type="password" autocomplete="current-password" required maxlength="128" :disabled="pending" />
      <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
      <button type="submit" class="login-submit" :disabled="pending">{{ pending ? '正在验证…' : '登录' }}</button>
      <p class="login-help">没有账户？ <RouteLink to="/register">申请注册账号</RouteLink></p>
    </form>
  </section>
</template>
<style scoped>
.login-panel { width: 100%; }
.login-context { margin-bottom: 32px; }
.login-context p { color: var(--auth-muted); margin: 0; font-size: 14px; line-height: 1.8; }
.login-form { display: flex; flex-direction: column; gap: 10px; }
.login-form label { font-size: 13px; font-weight: 600; }
.login-form input { margin-bottom: 14px; }
.login-submit { margin-top: 6px; }
.login-help { margin: 14px 0 0; color: var(--auth-muted); text-align: center; font-size: 13px; line-height: 2; }
.login-help a { display: inline-flex; align-items: center; min-height: 44px; font-weight: 600; }
.auth-error { margin: 0; }
</style>
